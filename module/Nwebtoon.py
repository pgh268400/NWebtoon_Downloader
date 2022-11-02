import errno
import multiprocessing
import os
import re
from multiprocessing.pool import ThreadPool
from time import sleep
from urllib import parse

import requests
from bs4 import BeautifulSoup
from requests import get

download_index = 1


class NWebtoon:
    def __init__(self, query):
        """
        검색어를 주고 객체를 생성하면 이 생성자에서 처리를 합니다.
        알아서 검색창을 띄어주고 사용자가 선택한 웹툰에 따라
        웹툰 객체가 웹툰의 정보를 가질 수 있게 합니다.
        :param query: 검색어
        """
        # 생성자에서 파이썬 인스턴스 변수 초기화
        # NID_AUT 와 NID_SES 는 나중에 get_session() 함수를 통해 받아올 것임.
        self.NID_SES = ""
        self.NID_AUT = ""

        exp = '[0-9]{5,6}'
        if 'titleId=' in query:  # 입력값에 titleid가 존재하면
            id_pattern = re.search(exp, query)
            if id_pattern:
                self.__title_id = id_pattern.group()
            else:
                self.__title_id = None  # titleid은 포함되어 있으나 이상한값
        else:
            input_is_id = re.match(exp, query)  # 문자열 시작부터 매칭
            if input_is_id:
                self.__title_id = query  # 입력값 자체가 ID
            else:  # 검색어면
                self.__title_id = self.search(query)

        req = requests.get(
            "https://comic.naver.com/webtoon/list.nhn?titleId=" + self.__title_id)
        soup = BeautifulSoup(req.content, 'html.parser')

        # title = 제목, num = 총화수, content = 웹툰 설명, type = 웹툰 타입, isadult = 성인웹툰 유무
        # 파이썬의 private 키워드 __ 를 통해 캡슐화를 구현하도록 하자.

        self.__title = soup.find("meta", property="og:title")[
            "content"]  # 타이틀 가져오기
        self.__content = soup.find("meta", property="og:description")[
            'content']  # 컨텐츠 가져오기

        table = soup.select("tr > td.title > a")[
            0]['onclick']  # a태그의 onclick 항목 가져오기
        # 총화수를 구하기위해 onclick을 , 로 쪼개고 쓸모없는 부분을 Replace로 날린다.
        self.__number = table.split(',')[3].replace(")", "")
        self.__number = int(self.__number.replace("'", ""))  # int 형식으로 변환한다.

        self.__wtype = soup.select('td.title > a')[0]['href']
        self.__wtype = self.__wtype.split('/')[1]

        adult_parse = soup.select(".mark_adult_thumb")
        self.__isadult = False
        if len(adult_parse) != 0:
            self.__isadult = True

    def set_session(self, NID_AUT, NID_SES):
        # NID_AUT, NID_SES 가져오기
        self.NID_AUT = NID_AUT
        self.NID_SES = NID_SES

    def search(self, keyword):
        lst = []
        req = requests.get(
            "https://comic.naver.com/search.nhn?keyword=" + keyword)
        soup = BeautifulSoup(req.content, 'html.parser')
        txt = soup.select("#content > div:nth-child(2) > ul.resultList")
        p = re.search('검색 결과가 없습니다.', str(txt))
        if p:
            input('검색 결과가 없습니다.')
            return None
        else:  # 검색결과가 있을경우
            txt = soup.find('ul', class_='resultList')
            for string in txt.find_all('a'):
                title = re.search('>(.*?)<', str(string))
                if title:
                    t = re.search('[0-9]{5,6}', string.get('href'))
                    if t:
                        lst.append([title.group(1), t.group()])

            print('-----웹툰 검색결과-----')
            for i, title in enumerate(lst):
                print(f'{i} {self.tag_remover(title[0])}')
            print('----------------------')
            index = int(input('선택할 웹툰의 번호를 입력해주세요 : '))
            title_id = str(lst[index][1])
            return title_id

    # 경로 금지 문자 제거, HTML문자 제거
    def filename_remover(self, string):
        # <tag>, &nbsp 등등 제거
        cleaner = re.compile('<.*?>|&([a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});')
        string = re.sub(cleaner, '', string)

        while string[-1] == '.':
            string = string[:-1]  # 끝에 . 제거 ex) test... -> test

        non_directory_letter = []
        if os.name == 'nt':
            non_directory_letter = ['/', ':', '*',
                                    '?', '<', '>', '|']  # 경로 금지 문자열 제거
        elif os.name == 'posix':
            non_directory_letter = [':', '*',
                                    '?', '<', '>', '|']  # 경로 금지 문자열 제거

        for str_ in non_directory_letter:
            if str_ in string:
                string = string.replace(str_, "")
        return string

    def tag_remover(self, string):
        # <tag>, &nbfs 등등 제거
        cleaner = re.compile('<.*?>|&([a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});')
        string = re.sub(cleaner, '', string)
        return string

    # URL 이미지 다운로드에 실제로 사용하는 함수
    def image_download(self, url, file_name):
        with open(file_name, "wb") as file:  # open in binary mode
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.119 Safari/537.36',
                'host': 'image-comic.pstatic.net'}
            response = get(url, headers=headers)  # get request
            if response.status_code == 200:
                file.write(response.content)  # write to file

    # 단일 이미지 다운로드
    def single_download(self, args):
        print(args, '화 다운로드 시작되었습니다')
        url = "https://comic.naver.com/" + self.__wtype + \
            "/detail.nhn?titleId=" + self.__title_id + "&no=" + args
        req = requests.get(url)
        soup = BeautifulSoup(req.content, 'html.parser')

        manga_title = soup.select('div.tit_area > div.view > h3')  # 웹툰 제목 가져오기
        # 리스트를 string 으로 바꾸고 불필요한 string 제거한다.
        manga_title = self.tag_remover(str(manga_title[0]))
        # path = str(self.__title) + '\\' + manga_title
        path = os.path.join(str(self.__title), manga_title)

        try:
            print("path : ", path)
            os.makedirs(path)
        except OSError as e:
            if e.errno != errno.EEXIST:
                print('폴더 생성중 오류가 발생하였습니다')
                raise
        image_url = soup.select('div.wt_viewer > img')
        j = 0
        for img in image_url:
            url = img['src']

            parsed = parse.urlparse(url)
            name, ext = os.path.splitext(parsed.path)

            # _path = path + "\\" + str(j) + ext
            _path = os.path.join(path, str(j) + ext)
            self.image_download(url, _path)
            j += 1
            print(url)
        input('다운로드가 완료되었습니다.')

    def multi_download(self, dialog):
        global download_index

        download_index = int(dialog.split('-')[0])
        core_count = multiprocessing.cpu_count() * 2
        download_range = dialog.split('-')
        results = ThreadPool(core_count).imap_unordered(self.p_image_download,
                                                        self.get_image_link(download_range))
        for link, path in results:
            print(link, path)

    # 이미지 링크 추출(경로 포함)
    def get_image_link(self, args):
        global download_index
        result = []
        for i in range(int(args[0]), int(args[1]) + 1):
            url = "https://comic.naver.com/" + self.__wtype + \
                "/detail.nhn?titleId=" + self.__title_id + "&no=" + str(i)
            cookies = {'NID_AUT': self.NID_AUT, 'NID_SES': self.NID_SES}
            req = requests.get(url, cookies=cookies)
            soup = BeautifulSoup(req.content, 'html.parser')
            manga_title = soup.select(
                'div.tit_area > div.view > h3')  # 웹툰 제목 가져오기
            # 리스트를 string 으로 바꾸고 불필요한 string 제거한다.
            manga_title = self.filename_remover(str(manga_title[0]))

            idx = "[" + str(download_index) + "] "  # 순번매기기 형식 [0], [1]...

            # running_path = os.path.abspath(os.path.dirname(__file__))
            img_path = os.path.join(str(
                self.__title), idx + manga_title)

            path = self.filename_remover(img_path)

            # print title, idx, manga_title
            # print("title : ", self.__title, "idx : ",
            #       idx, "manga_title : ", manga_title)

            try:
                print(f'[디렉토리 생성] {manga_title}')
                os.makedirs(path)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    print('폴더 생성중 오류가 발생하였습니다')
                    raise

            image_url = soup.select('div.wt_viewer > img')
            j = 0
            for img in image_url:
                url = img['src']

                parsed = parse.urlparse(url)
                name, ext = os.path.splitext(parsed.path)
                # _path = path + "\\" + str(j) + ext
                _path = os.path.join(path, str(j) + ext)

                if not 'img-ctguide-white.png' in url:  # 컷툰이미지 제거하기
                    # URL,PATH 형식으로 List에 저장
                    result.append([url, self.tag_remover(_path)])
                j += 1
            download_index = download_index + 1
        return result

    # 다중 이미지 다운로드
    def p_image_download(self, data):
        # 참고 : 이미지서버 자체는 로그인 여부 판단안함.
        for i in range(3):  # 총 3회 시도
            try:
                uri, path = data  # [URL, PATH] 형태로 들어온 리스트를 읽어냄
                self.image_download(uri, path)
                return data
                break
            except requests.exceptions.ConnectionError:  # 커넥션 오류시(max retires)
                print("연결 실패.. 다시 시도중..")
                sleep(1000)
                self.p_image_download(data)
                continue
            except Exception as ex:
                print("오류가 발생하여 오류를 파일에 기록합니다.")
                error = str(ex)
                print(error)
                with open("error_log.txt", "a") as file:  # append 모드
                    file.write(error)
                    file.close()
                break

    # Getter 함수 구현 (프로퍼티)
    @property
    def title(self):
        return self.__title

    @property
    def title_id(self):
        return self.__title_id

    @property
    def content(self):
        return self.__content

    @property
    def wtype(self):
        return self.__wtype

    @property
    def isadult(self):
        return self.__isadult

    @property
    def number(self):
        return self.__number
