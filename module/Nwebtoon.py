import errno
import json
import multiprocessing
import os
import re
from multiprocessing.pool import ThreadPool
from time import sleep
from urllib import parse
from rich import print
import requests
from bs4 import BeautifulSoup
from requests import get

# 경로는 main.py의 위치를 기준으로 import함에 주의
from module.Headers import headers

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

        res = requests.get(
            f"https://comic.naver.com/api/article/list/info?titleId={self.__title_id}")

        soup = BeautifulSoup(res.content, 'html.parser')

        # json.loads()를 사용하여 JSON 응답을 파이썬 객체로 변환
        res_json = json.loads(res.content)

        # title = 제목, num = 총화수, content = 웹툰 설명, type = 웹툰 타입, isadult = 성인웹툰 유무
        # 파이썬의 private 키워드 __ 를 통해 캡슐화를 구현하도록 하자.

        # print(res_json)

        self.__title = res_json["titleName"]  # 웹툰 제목
        self.__content = res_json["synopsis"]  # 컨텐츠 가져오기
        # 웹툰 타입 : webtoon / challenge / bestChallenge : url에서 사용하는 것
        self.__wtype = res_json["webtoonLevelCode"]
        if self.__wtype == "WEBTOON":
            self.__wtype = "webtoon"
        elif self.__wtype == "CHALLENGE":
            self.__wtype = "challenge"
        elif self.__wtype == "BEST_CHALLENGE":
            self.__wtype = "bestChallenge"

        # no에 아주 큰 값을 넣어서 리다이렉션되는 페이지에서 접근가능한 총화수를 가져옴
        res = requests.get(
            f"https://comic.naver.com/{self.__wtype}/detail?titleId={self.__title_id}&no=999999", allow_redirects=True)
        # print(
        #     f"https://comic.naver.com/{self.__wtype}/detail?titleId={self.__title_id}&no=999999")
        redirected_url = res.url

        # 웹툰 리다이렉트 주소가 로그인 주소인 경우 성인웹툰임
        if ("https://nid.naver.com/nidlogin.login" in redirected_url):
            self.__isadult = True

            # NID_AUT, NID_SES 쿠키를 받아서 다시 요청
            print('성인 웹툰입니다. 로그인 정보를 입력해주세요.')
            NID_AUT = input("NID_AUT : ")
            NID_SES = input("NID_SES : ")
            self.set_session(NID_AUT, NID_SES)  # 객체에 세션 데이터 넘기기

            cookies = {"NID_AUT": NID_AUT, "NID_SES": NID_SES}
            res = requests.get(
                f"https://comic.naver.com/{self.__wtype}/detail?titleId={self.__title_id}&no=999999", cookies=cookies, allow_redirects=True)
            redirected_url = res.url

        # url에서 no 부분만 가져오기
        match = re.search(r'no=(\d+)', redirected_url)

        if match:
            # 웹툰 총 화수 (반드시 int타입 이여야함.)
            self.__number = int(match.group(1))
        else:
            input("Error : No match found.")
            return

        adult_parse = res_json["age"]["type"]

        if adult_parse == "RATE_18":
            self.__isadult = True
        else:
            self.__isadult = False

    def set_session(self, NID_AUT, NID_SES):
        # NID_AUT, NID_SES 설정하기
        self.NID_AUT = NID_AUT
        self.NID_SES = NID_SES

    # 웹툰 검색 API searchViewList 웹툰 / 도전만화 / 베스트도전 만화에 따라 파싱해주는 함수
    def search_api_parser(self, res_json, type):
        if type == "webtoon":
            webtoon_lst = res_json["searchWebtoonResult"]["searchViewList"]
        elif type == "best_challenge":
            webtoon_lst = res_json["searchBestChallengeResult"]["searchViewList"]
        elif type == "challenge":
            webtoon_lst = res_json["searchChallengeResult"]["searchViewList"]

        # enumerate() 함수는 기본적으로 인덱스와 원소로 이루어진 튜플(tuple)을 만들어준다
        # ex) enumerate([1,2,3,4,5]) -> [(0,1), (1,2), (2,3), (3,4), (4,5)]
        # enumerate() 함수의 두번째 인자는 인덱스의 시작값을 지정할 수 있다.
        # ex) enumerate([1,2,3,4,5], 1) -> [(1,1), (2,2), (3,3), (4,4), (5,5)]
        # 우리는 만들어진 튜플을 파이썬의 (,) unpacking 기능을 이용하여 인덱스와 원소를 각각의 변수에 저장할 것이다.
        # 리스트를 반복하면서 인덱스를 활용하는 파이썬 스러운 방법이다! So cool!
        # 라고 잘 적어놨으나 여기서 i 인덱스를 만들어줄 이유가 없어서 일단은.. enumerate() 함수의 원리만 이해하도록 하자 ㅎㅎ;
        result = []
        for i, search_view in enumerate(webtoon_lst, 1):
            title_name = search_view['titleName']
            display_author = search_view['displayAuthor']
            genre_list = search_view['genreList']
            article_total_count = search_view['articleTotalCount']
            last_article_service_date = search_view['lastArticleServiceDate']
            synopsis = search_view['synopsis']

            genre_names = [genre['description'] for genre in genre_list]

            output_str = f'{title_name}\n글/그림 : {display_author} | 장르 : {" / ".join(genre_names)} | 총 {article_total_count}화 | 최종 업데이트 {last_article_service_date}\n{synopsis}'
            result.append((output_str, search_view['titleId']))

        return result

    def search(self, keyword):
        lst = []
        # 네이버 웹툰 개편으로 API 링크에 동적으로 요청해서 렌더링 하는 방식으로 바뀜 (2023-03-03)
        # 웹툰 페이지에선 JS로 동적으로 로딩하므로 웹툰 페이지가 아니라 API 요청으로 검색 결과를 가져와야함.
        # requests 는 JS 로딩한 데이터는 가져올 수 없고 단순히 요청 & 응답에 대한 데이터만 가져올 수 있기 때문 =ㅅ=

        search_api_url = f"https://comic.naver.com/api/search/all?keyword={keyword}"
        res = requests.get(search_api_url, headers=headers)

        # json.loads()를 사용하여 JSON 응답을 파이썬 객체로 변환
        res_json = json.loads(res.content)

        # json.dumps()를 사용하여 파이썬 객체를 이쁘게 출력
        # print(json.dumps(res_json, indent=4, ensure_ascii=False))

        # 일반 웹툰, 베스트 도전, 도전만화 갯수 파싱
        webtoon_cnt = res_json["searchWebtoonResult"]["totalCount"]
        best_challenge_cnt = res_json["searchBestChallengeResult"]["totalCount"]
        challenge_cnt = res_json["searchChallengeResult"]["totalCount"]

        soup = BeautifulSoup(res.content, 'html.parser')
        txt = soup.select("#content > div:nth-child(2) > ul.resultList")

        if (webtoon_cnt + best_challenge_cnt + challenge_cnt) == 0:
            input('검색 결과가 없습니다.')
            return None
        else:  # 검색결과가 있을경우
            webtoon_lst = res_json["searchWebtoonResult"]["searchViewList"]
            # print(webtoon_lst)

            global_i = 1

            print(f'[bold green]-----웹툰 검색결과-----[/bold green]')
            print(f"[상위 5개] ---- 총 {webtoon_cnt}개")
            webtoon_result = self.search_api_parser(res_json, "webtoon")
            for element in webtoon_result:
                print(f"[bold red]{global_i}.[/bold red] {element[0]}")
                global_i += 1

            print(f'[bold green]-----베스트 도전 검색결과-----[/bold green]')
            print(f"[상위 5개] ---- 총 {best_challenge_cnt}개")
            best_challenge_result = self.search_api_parser(
                res_json, "best_challenge")
            for element in best_challenge_result:
                print(f"[bold red]{global_i}.[/bold red] {element[0]}")
                global_i += 1

            print(f'[bold green]-----도전만화 검색결과-----[/bold green]')
            print(f"[상위 5개] ---- 총 {challenge_cnt}개")
            challenge_result = self.search_api_parser(res_json, "challenge")
            for element in challenge_result:
                print(f"[bold red]{global_i}.[/bold red] {element[0]}")
                global_i += 1

            all_result = webtoon_result + best_challenge_result + \
                challenge_result  # use list comprehension

            index = int(input('선택할 웹툰의 번호를 입력해주세요 : '))
            title_id = str(all_result[index - 1][1])
            # print(f'선택한 웹툰의 title_id : {title_id}')
            return title_id

    # 경로 금지 문자 제거, HTML문자 제거
    def filename_remover(self, string):

        # <tag>, &nbsp 등등 제거
        cleaner = re.compile('<.*?>|&([a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});')
        string = re.sub(cleaner, '', string)

        # 폴더에 저장할 수 없는 문자 제거
        # non_directory_letter = []
        # if os.name == 'nt':
        #     # non_directory_letter = ['/', ':', '*',
        #     #                         '?', '<', '>', '|']  # 경로 금지 문자열 제거
        #     non_directory_letter = ['\\', '/',
        #                             ':', '*', '?', '"', '<', '>', '|']

        #     # non_directory_dict = {'\\', '/',
        #     #                       ':': '\U000002f8', '*': '⚹', '?', '"', '<', '>', '|'}
        # elif os.name == 'posix':
        #     non_directory_letter = [':', '*',
        #                             '?', '<', '>', '|']  # 경로 금지 문자열 제거 (리눅스에선 / 가 경로 구분자라 제거하지 않음)

        # for char in non_directory_letter:
        #     if char in string:
        #         string = string.replace(char, "")

        # 폴더에 들어갈 수 없는 특수문자를 들어갈 수 있는
        # 특수한 유니코드 문자 (겉보기에 똑같은 문자)로 치환 시킨다.
        table = str.maketrans('\\/:*?"<>|.', "￦／：＊？＂˂˃｜．")
        string = string.translate(table)

        # \t 과 \n제거 (\t -> 공백 , \n -> 공백)
        table = str.maketrans('\t\n', "  ")
        string = string.translate(table)

        # 끝에 . 제거 ex) test... -> test
        # while string[-1] == '.':
        #     string = string[:-1]
        # return string
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
        url = f"https://comic.naver.com/{self.__wtype}/detail.nhn?titleId={self.__title_id}&no={args}"
        req = requests.get(url)
        soup = BeautifulSoup(req.content, 'html.parser')

        manga_title = soup.select('div.tit_area > div.view > h3')[
            0].get_text()  # 웹툰 제목 가져오기
        # 리스트를 string 으로 바꾸고 불필요한 string 제거한다.
        manga_title = self.filename_remover(manga_title)
        directory_title = self.filename_remover(self.__title)
        path = os.path.join(directory_title, manga_title)

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

    def multi_download(self, dialog: str):
        global download_index

        # dialog example
        # 1-10

        # 멀티 프로세싱을 이용한 병렬 다운로드 처리
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
            # fstring으로 변경
            url = f"https://comic.naver.com/{self.__wtype}/detail?titleId={self.__title_id}&no={i}"

            cookies = {'NID_AUT': self.NID_AUT, 'NID_SES': self.NID_SES}
            req = requests.get(url, cookies=cookies)
            soup = BeautifulSoup(req.content, 'html.parser')

            manga_title = soup.select('#subTitle_toolbar')[
                0].get_text()  # 웹툰 제목 가져오기
            manga_title = manga_title.strip()  # 양 끝 공백 제거
            # 리스트를 string 으로 바꾸고 불필요한 string 제거한다.
            manga_title = self.filename_remover(manga_title)

            # idx = "[" + str(download_index) + "] "  # 순번매기기 형식 [0], [1]...
            idx = f"[{download_index}] "

            # running_path = os.path.abspath(os.path.dirname(__file__))
            directory_title = self.filename_remover(self.__title)
            img_path = os.path.join(directory_title, idx + manga_title)

            # path = self.filename_remover(img_path)
            path = img_path

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
    @ property
    def title(self):
        return self.__title

    @ property
    def title_id(self):
        return self.__title_id

    @ property
    def content(self):
        return self.__content

    @ property
    def wtype(self):
        return self.__wtype

    @ property
    def isadult(self):
        return self.__isadult

    @ property
    def number(self):
        return self.__number
