import errno
import json
import multiprocessing
import os
import re
from multiprocessing.pool import ThreadPool
from time import sleep
from typing import Literal
from urllib import parse
from rich import print
import requests
from bs4 import BeautifulSoup
from requests import get

# 경로는 main.py의 위치를 기준으로 import함에 주의
from module.Headers import headers, image_headers
from module.Settings import Setting
from type.api_article_list_info_v2 import NWebtoonMainData
from type.api_search_all import NWebtoonSearchData, searchView

download_index = 1  # 다운로드 인덱스 카운트


class NWebtoon:
    ERROR_PATH = "./error_log.txt"  # 에러 로그 경로
    DOWNLOAD_PATH = "./Webtoon_Download"  # 다운로드 경로

    def __init__(self, query: str) -> None:
        """
        검색어를 주고 객체를 생성하면 이 생성자에서 처리를 합니다.
        알아서 검색창을 띄어주고 사용자가 선택한 웹툰에 따라
        웹툰 객체가 웹툰의 정보를 가질 수 있게 합니다.
        :param query: 검색어
        """
        # 생성자에서 파이썬 인스턴스 변수 초기화
        # NID_AUT 와 NID_SES 는 나중에 get_session() 함수를 통해 받아올 것임.
        self.NID_SES: str = ""
        self.NID_AUT: str = ""

        # 이외에 필요한 변수들 타입 힌트 이용하여 초기화
        # title = 제목, number = 총화수, content = 웹툰 설명, type = 웹툰 타입, isadult = 성인웹툰 유무
        # 파이썬의 private 키워드 __ 를 통해 캡슐화를 구현하도록 하자.
        self.__title_id: str = ""
        self.__title: str = ""
        self.__isadult: bool = False
        self.__wtype: Literal["webtoon",
                              "challenge", "bestChallenge"] = "webtoon"
        self.__number: int = 0
        self.__content: str = ""

        exp = '[0-9]{5,6}'
        if 'titleId=' in query:  # 입력값에 titleid가 존재하면
            id_pattern = re.search(exp, query)
            if id_pattern:
                self.__title_id = id_pattern.group()
            else:
                input("Error : titleid는 5~6자리의 숫자입니다. 입력값을 확인해주세요.")
                exit()  # 프로그램 강제 종료
        else:
            input_is_id = re.match(exp, query)  # 문자열 시작부터 매칭
            if input_is_id:
                self.__title_id = query  # 입력값 자체가 ID
            else:  # 검색어면
                self.__title_id = self.search(query)

        res = requests.get(
            f"https://comic.naver.com/api/article/list/info?titleId={self.__title_id}")

        # json.loads()를 사용하여 JSON 응답을 파이썬 객체로 변환
        res_json: dict = json.loads(res.content)

        # JSON 응답 딕셔너리를 미리 타입 정의한 Dataclass로 변환 (type-safety)
        webtoon: NWebtoonMainData = NWebtoonMainData.from_dict(  # type: ignore
            res_json)

        self.__title = webtoon.titleName  # 웹툰 제목
        self.__content = webtoon.synopsis  # 컨텐츠 가져오기

        # 웹툰 타입 : webtoon / challenge / bestChallenge : url에서 사용하는 것
        json_level_code = webtoon.webtoonLevelCode
        if json_level_code == "WEBTOON":
            self.__wtype = "webtoon"
        elif json_level_code == "CHALLENGE":
            self.__wtype = "challenge"
        elif json_level_code == "BEST_CHALLENGE":
            self.__wtype = "bestChallenge"

        # no에 아주 큰 값을 넣어서 리다이렉션되는 페이지에서 접근가능한 총화수를 가져옴
        res = requests.get(
            f"https://comic.naver.com/{self.__wtype}/detail?titleId={self.__title_id}&no=999999", allow_redirects=True)
        redirected_url = res.url

        cookies = {}

        # 웹툰 리다이렉트 주소가 로그인 주소인 경우 성인웹툰임
        if ("https://nid.naver.com/nidlogin.login" in redirected_url):
            self.__isadult = True

            # NID_AUT, NID_SES 쿠키를 받아서 다시 요청
            print('성인 웹툰입니다. 로그인 정보를 입력해주세요.')
            NID_AUT = input("NID_AUT : ")
            NID_SES = input("NID_SES : ")
            self.set_session(NID_AUT, NID_SES)  # 객체에 세션 데이터 넘기기

            cookies = {"NID_AUT": NID_AUT, "NID_SES": NID_SES}
            # res = requests.get(
            #     f"https://comic.naver.com/{self.__wtype}/detail?titleId={self.__title_id}&no=999999", cookies=cookies, allow_redirects=True)
            # redirected_url = res.url

        # url에서 no 부분만 가져오기
        # ex) https://comic.naver.com/webtoon/detail?titleId=20853&no=100 -> 100
        # match = re.search(r'no=(\d+)', redirected_url)

        # if match:
        #     # 웹툰 총 화수 (반드시 int타입 이여야함.)
        #     self.__number = int(match.group(1))
        # else:
        #     input(
        #         "Error : 웹툰의 총 화수를 가져오지 못했습니다.\n성인웹툰이라면 NID_AUT, NID_SES의 오타 여부를, 일반 웹툰이라면 인터넷 연결 상태를 확인해주세요.")
        #     exit()

        res = requests.get(
            f"https://comic.naver.com/api/article/list?titleId={self.__title_id}&page=1", cookies=cookies)
        res_json: dict = json.loads(res.content)

        self.__number = int(res_json['totalCount'])

        adult_parse = webtoon.age.type
        print(webtoon.age.type)
        if adult_parse == "RATE_18":
            self.__isadult = False
        else:
            self.__isadult = False

    def set_session(self, NID_AUT: str, NID_SES: str) -> None:
        # NID_AUT, NID_SES 설정하기
        self.NID_AUT = NID_AUT
        self.NID_SES = NID_SES

    # 웹툰 검색 API searchViewList 웹툰 / 도전만화 / 베스트도전 만화에 따라 파싱해주는 함수
    def search_api_parser(self, webtoon: NWebtoonSearchData, type: Literal["webtoon",
                                                                           "challenge", "bestChallenge"]):
        if type == "webtoon":
            webtoon_lst = webtoon.searchWebtoonResult.searchViewList
        elif type == "bestChallenge":
            webtoon_lst = webtoon.searchBestChallengeResult.searchViewList
        elif type == "challenge":
            webtoon_lst = webtoon.searchChallengeResult.searchViewList

        # enumerate() 함수는 기본적으로 인덱스와 원소로 이루어진 튜플(tuple)을 만들어준다
        # ex) enumerate([1,2,3,4,5]) -> [(0,1), (1,2), (2,3), (3,4), (4,5)]
        # enumerate() 함수의 두번째 인자는 인덱스의 시작값을 지정할 수 있다.
        # ex) enumerate([1,2,3,4,5], 1) -> [(1,1), (2,2), (3,3), (4,4), (5,5)]
        # 우리는 만들어진 튜플을 파이썬의 (,) unpacking 기능을 이용하여 인덱스와 원소를 각각의 변수에 저장할 것이다.
        # 리스트를 반복하면서 인덱스를 활용하는 파이썬 스러운 방법이다! So cool!
        # 라고 잘 적어놨으나 여기서 i 인덱스를 만들어줄 이유가 없어서 일단은.. enumerate() 함수의 원리만 이해하도록 하자 ㅎㅎ;
        result = []
        for i, search_view in enumerate(webtoon_lst, 1):
            search_view: searchView  # type hinting

            title_name = search_view.titleName
            display_author = search_view.displayAuthor
            genre_list = search_view.genreList
            article_total_count = search_view.articleTotalCount
            last_article_service_date = search_view.lastArticleServiceDate
            synopsis = search_view.synopsis

            genre_names = [genre.description for genre in genre_list]

            output_str = f'{title_name}\n글/그림 : {display_author} | 장르 : {" / ".join(genre_names)} | 총 {article_total_count}화 | 최종 업데이트 {last_article_service_date}\n{synopsis}'
            result.append((output_str, search_view.titleId))

        return result

    def search(self, keyword: str) -> str:
        # 네이버 웹툰 개편으로 API 링크에 동적으로 요청해서 렌더링 하는 방식으로 바뀜 (2023-03-03)
        # 웹툰 페이지에선 JS로 동적으로 로딩하므로 웹툰 페이지가 아니라 API 요청으로 검색 결과를 가져와야함.
        # requests 는 JS 로딩한 데이터는 가져올 수 없고 단순히 요청 & 응답에 대한 데이터만 가져올 수 있기 때문 =ㅅ=

        while True:
            search_api_url = f"https://comic.naver.com/api/search/all?keyword={keyword}"
            res = requests.get(search_api_url, headers=headers)

            # json.loads()를 사용하여 JSON 응답을 파이썬 객체로 변환
            res_json = json.loads(res.content)

            # json 응답을 미리 정의한 dataclass 타입으로 변환(type-safety)
            webtoon: NWebtoonSearchData = NWebtoonSearchData.from_dict(  # type: ignore
                res_json)

            # 일반 웹툰, 베스트 도전, 도전만화 갯수 파싱
            webtoon_cnt = webtoon.searchWebtoonResult.totalCount
            best_challenge_cnt = webtoon.searchBestChallengeResult.totalCount
            challenge_cnt = webtoon.searchChallengeResult.totalCount

            if (webtoon_cnt + best_challenge_cnt + challenge_cnt) == 0:
                keyword = ""
                while not keyword.strip():
                    keyword = input('검색 결과가 없습니다. 다시 검색해주세요 : ')
                # exit()
            else:
                break

        # webtoon_lst = res_json["searchWebtoonResult"]["searchViewList"]
        # print(webtoon_lst)

        i = 1

        print(f'[bold green]-----웹툰 검색결과-----[/bold green]')
        print(f"[상위 5개] ---- 총 {webtoon_cnt}개")
        webtoon_result = self.search_api_parser(webtoon, "webtoon")
        for element in webtoon_result:
            print(f"[bold red]{i}.[/bold red] {element[0]}")
            i += 1

        print(f'[bold green]-----베스트 도전 검색결과-----[/bold green]')
        print(f"[상위 5개] ---- 총 {best_challenge_cnt}개")
        best_challenge_result = self.search_api_parser(
            webtoon, "bestChallenge")
        for element in best_challenge_result:
            print(f"[bold red]{i}.[/bold red] {element[0]}")
            i += 1

        print(f'[bold green]-----도전만화 검색결과-----[/bold green]')
        print(f"[상위 5개] ---- 총 {challenge_cnt}개")
        challenge_result = self.search_api_parser(webtoon, "challenge")
        for element in challenge_result:
            print(f"[bold red]{i}.[/bold red] {element[0]}")
            i += 1

        all_result = webtoon_result + best_challenge_result + \
            challenge_result  # use list comprehension

        msg = '>>> 선택할 웹툰의 번호를 입력해주세요 : '
        while True:
            try:
                index = int(input(msg))
                if 1 <= index <= len(all_result):
                    break  # 정상 범위의 숫자를 입력했을 경우 while문 탈출
                else:
                    msg = ">>> 범위를 벗어났습니다. 다시 입력해주세요 : "
            except ValueError:
                # 숫자가 아닌 다른 문자를 입력했을 경우 index = int(input(msg)) 부분에서 바로 여기로 점프됨.
                msg = ">>> 숫자가 아닙니다. 다시 입력해주세요 : "

        # 위의 반복문을 탈출했다는 것은 정상적인 범위의 숫자를 입력했음을 의미.

        title_id = str(all_result[index - 1][1])
        # print(f'선택한 웹툰의 title_id : {title_id}')
        return title_id

    # 경로 금지 문자 제거, HTML문자 제거
    def filename_remover(self, string: str) -> str:
        # 1. 폴더에 들어갈 수 없는 특수문자를 들어갈 수 있는
        # 특수한 유니코드 문자 (겉보기에 똑같은 문자)로 치환 시킨다.
        table = str.maketrans('\\/:*?"<>|.', "￦／：＊？＂˂˃｜．")
        processed_string: str = string.translate(table)

        # 2. \t 과 \n제거 (\t -> 공백 , \n -> 공백)
        table = str.maketrans('\t\n', "  ")
        processed_string = processed_string.translate(table)
        return processed_string

    def tag_remover(self, string: str) -> str:
        # <tag>, &nbfs 등등 제거
        cleaner = re.compile('<.*?>|&([a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});')
        string = re.sub(cleaner, '', string)
        return string

    # URL 이미지 다운로드에 실제로 사용하는 함수
    def image_download(self, url: str, file_name: str) -> None:
        with open(file_name, "wb") as file:  # open in binary mode
            response = get(url, headers=image_headers)  # get request
            if response.status_code == 200:
                file.write(response.content)  # write to file

    def multi_download(self, start_index: int, end_index: int) -> None:
        global download_index

        # dialog example
        # 1-10

        # 멀티 프로세싱을 이용한 병렬 다운로드 처리
        # download_index = int(dialog.split('-')[0])
        download_index = start_index
        thread_count = multiprocessing.cpu_count() * 2

        # 1. self.get_image_link 에서 이미지 링크를 동기적으로 일괄 추출해서 리스트로 제공하면
        # 2. p_image_download 함수에 병렬적(비동기로 실행)으로 전달되어 다운로드가 처리됨.
        # 3. 결과는 리스트로 반환되는데, 이 리스트는 순서가 보장되지 않음. (by imap_unordered)

        # self.get_image_link 자체는 동기적으로 처리되기 때문에 이때 디렉토리 생성은 순서가 보장되며, 속도를 더 늘리고 싶다면
        # self.get_image_link 함수 역시 병렬 처리로 코드를 변경하면 됨. (not for, but imap_unordered)
        # 아직은 self.get_image_link 은 병렬 처리 하고 있지 않음.
        # 결론적으로 네트워크 I/O에 의한 웹툰 다운로드 속도를 최대한 높이기 위해 이미지 다운로드를 하는 부분 p_image_download 만
        # 병렬적으로 처리되고 있는 것.

        results = ThreadPool(thread_count).imap_unordered(self.p_image_download,
                                                          self.get_image_link(start_index, end_index))

        for link, path in results:
            print(link, path)

    # 이미지 링크 추출(경로 포함)
    def get_image_link(self, start_index: int, end_index: int):
        global download_index

        result = []
        for i in range(start_index, end_index + 1):
            # fstring으로 변경
            url = f"https://comic.naver.com/{self.__wtype}/detail?titleId={self.__title_id}&no={i}"
            cookies = {'NID_AUT': self.NID_AUT, 'NID_SES': self.NID_SES}
            req = requests.get(url, cookies=cookies)
            soup = BeautifulSoup(req.content, 'html.parser')

            # 만화가 없는 페이지일 경우 리스트에 추가하지 않음.
            if not soup.select('#subTitle_toolbar'):
                print(
                    f'no={i}가 없습니다. 순번이 존재 하지 않거나 미리보기, 유료화된 페이지입니다. 다운로드 하지 않고 SKIP 합니다.')
                continue

            manga_title = soup.select('#subTitle_toolbar')[
                0].get_text()  # 웹툰 제목 가져오기
            manga_title = manga_title.strip()  # 양 끝 공백 제거
            # 리스트를 string 으로 바꾸고 불필요한 string 제거한다.
            manga_title = self.filename_remover(manga_title)

            # 설정값 읽어오기 (폴더 제로필)
            s = Setting()
            folder_zfill_cnt = s.get_zero_fill('Folder')

            # idx = "[" + str(download_index) + "] "  # 순번매기기 형식 [0], [1]...
            idx = f"[{str(download_index).zfill(folder_zfill_cnt)}] "

            # running_path = os.path.abspath(os.path.dirname(__file__))
            directory_title = self.filename_remover(self.__title)
            img_path = os.path.join(directory_title, idx + manga_title)

            # path = self.filename_remover(img_path)
            path = img_path

            # download_path 와 path 경로 합치기
            path = os.path.join(NWebtoon.DOWNLOAD_PATH, path)

            # print(f'[다운로드 경로] {path}')

            # download_path 폴더 없으면 생성
            if not os.path.exists(NWebtoon.DOWNLOAD_PATH):
                os.makedirs(NWebtoon.DOWNLOAD_PATH)

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

            s = Setting()
            image_zfill_cnt = s.get_zero_fill('Image')
            for img in image_url:
                url = img['src']

                parsed = parse.urlparse(url)
                name, ext = os.path.splitext(parsed.path)
                _path = os.path.join(path, str(j).zfill(image_zfill_cnt) + ext)

                if not 'img-ctguide-white.png' in url:  # 컷툰이미지 제거하기
                    # URL,PATH 형식으로 List에 저장
                    result.append([url, self.tag_remover(_path)])
                j += 1

            download_index += 1
        return result

    # 다중 이미지 다운로드
    def p_image_download(self, data):

        if not data:
            return

        # 참고 : 이미지서버 자체는 로그인 여부 판단안함.
        for i in range(3):  # 총 3회 시도
            try:
                uri, path = data  # [URL, PATH] 형태로 들어온 리스트를 읽어냄
                self.image_download(uri, path)
                return data
            except requests.exceptions.ConnectionError:  # 커넥션 오류시(max retires)
                print("연결 실패.. 다시 시도중..")
                sleep(1000)
                self.p_image_download(data)
                continue
            except Exception as ex:
                input("오류가 발생하여 오류를 파일에 기록합니다.")
                error = str(ex)
                input(error)
                with open(NWebtoon.ERROR_PATH, "a") as file:  # append 모드
                    file.write(error)
                    file.close()
                break

    # Getter 함수 구현 (프로퍼티)
    @ property
    def title(self) -> str:
        return self.__title

    @ property
    def title_id(self) -> str:
        return self.__title_id

    @ property
    def content(self) -> str:
        return self.__content

    @ property
    def wtype(self) -> Literal['webtoon', 'challenge', 'bestChallenge']:
        return self.__wtype

    @ property
    def isadult(self) -> bool:
        return self.__isadult

    @ property
    def number(self) -> int:
        return self.__number
