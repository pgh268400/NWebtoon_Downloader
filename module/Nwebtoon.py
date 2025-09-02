import asyncio
import errno
import json
import multiprocessing
import os
import re
from multiprocessing.pool import ThreadPool
import sys
from time import sleep
from typing import Literal
from urllib import parse
import aiohttp
from rich import print
import requests
from bs4 import BeautifulSoup
from requests import get
import tqdm

# 경로는 main.py의 위치를 기준으로 import함에 주의
from module.file_processor import FileProcessor
from module.headers import headers, image_headers
from module.settings import FileSettingType, Setting
from type.api.comic_info import NWebtoonMainData, WebtoonCode, WebtoonType
from type.api.search_all import NWebtoonSearchData, SearchView
from type.thread_pool_results import (
    EpisodeResults,
    EpisodeUrlTuple,
    UrlPathTuple,
    UrlPathListResults,
)


download_index = 1  # 다운로드 인덱스 카운트


class NWebtoon:
    def __init__(self, query: str) -> None:
        """
        검색어를 주고 객체를 생성하면 이 생성자에서 처리를 합니다.
        알아서 검색창을 띄어주고 사용자가 선택한 웹툰에 따라
        웹툰 객체가 웹툰의 정보를 가질 수 있게 합니다.
        :param query: 검색어 (또는 웹툰 TITLE ID, URL 이 될수도 있음)
        """
        # 생성자에서 파이썬 인스턴스 변수 초기화 ======================================

        self.__settings = Setting()  # 설정 파일 관리 객체 생성
        self.__file_processor = FileProcessor()  # 폴더 / 파일 특수문자 제거용 객체

        # NID_AUT 와 NID_SES 는 나중에 get_session() 함수를 통해 받아올 것임.
        self.NID_SES: str = ""
        self.NID_AUT: str = ""

        # 이외에 필요한 변수들 타입 힌트 이용하여 초기화
        # title = 제목, number = 총화수, content = 웹툰 설명, type = 웹툰 타입, isadult = 성인웹툰 유무
        # 파이썬의 private 키워드 __ 를 통해 캡슐화를 구현하도록 하자.
        self.__title_id: str = ""
        self.__title: str = ""
        self.__isadult: bool = False
        self.__wtype: WebtoonType = WebtoonType.webtoon
        self.__number: int = 0
        self.__content: str = ""

        exp = "[0-9]{5,6}"
        if "titleId=" in query:  # 입력값에 titleid가 존재하면
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
            f"https://comic.naver.com/api/article/list/info?titleId={self.__title_id}"
        )

        # json.loads()를 사용하여 JSON 응답을 파이썬 객체로 변환
        json_res: dict = json.loads(res.content)

        # JSON 응답 딕셔너리를 미리 타입 정의한 Dataclass로 변환 (type-safety)
        webtoon: NWebtoonMainData = NWebtoonMainData.from_dict(json_res)

        self.__title = webtoon.titleName  # 웹툰 제목

        # 웹툰 제목에서 특수문자 -> 유니코드 문자로 변환 (폴더로 사용할 수 없는 문자 제거)
        self.__title = self.__file_processor.remove_forbidden_str(self.__title)

        self.__content = webtoon.synopsis  # 컨텐츠 가져오기

        # 웹툰 타입 : webtoon / challenge / bestChallenge : url에서 사용하는 것
        json_level_code = webtoon.webtoonLevelCode
        if json_level_code == WebtoonCode.WEBTOON:
            self.__wtype = WebtoonType.webtoon
        elif json_level_code == WebtoonCode.CHALLENGE:
            self.__wtype = WebtoonType.challenge
        elif json_level_code == WebtoonCode.BEST_CHALLENGE:
            self.__wtype = WebtoonType.bestChallenge

        # no에 아주 큰 값을 넣어서 리다이렉트되는 주소를 가져옴
        res = requests.get(
            f"https://comic.naver.com/{self.__wtype}/detail?titleId={self.__title_id}&no=999999",
            allow_redirects=True,
        )
        redirected_url = res.url

        cookies = {}

        # 웹툰 리다이렉트 주소가 로그인 주소인 경우 성인웹툰임
        if "https://nid.naver.com/nidlogin.login" in redirected_url:
            self.__isadult = True

            # NID_AUT, NID_SES 쿠키를 받아서 다시 요청
            print("성인 웹툰입니다. 로그인 정보를 입력해주세요.")
            NID_AUT = input("NID_AUT : ")
            NID_SES = input("NID_SES : ")
            self.set_session(NID_AUT, NID_SES)  # 객체에 세션 데이터 넘기기 : Setter
            cookies = {"NID_AUT": NID_AUT, "NID_SES": NID_SES}

        res = requests.get(
            f"https://comic.naver.com/api/article/list?titleId={self.__title_id}&page=1",
            cookies=cookies,
        )
        json_res: dict = json.loads(res.content)

        self.__number = int(json_res["totalCount"])

        adult_parse = webtoon.age.type
        # print(webtoon.age.type)
        if adult_parse == "RATE_18":
            self.__isadult = False
        else:
            self.__isadult = False

    def set_session(self, NID_AUT: str, NID_SES: str) -> None:
        # NID_AUT, NID_SES 설정하기
        self.NID_AUT = NID_AUT
        self.NID_SES = NID_SES

    # 웹툰 검색 API searchViewList 웹툰 / 도전만화 / 베스트도전 만화에 따라 파싱해주는 함수
    def search_api_parser(
        self,
        webtoon: NWebtoonSearchData,
        type: Literal["webtoon", "challenge", "bestChallenge"],
    ):
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
            search_view: SearchView  # type hinting

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

            # JSON 응답을 파일로 저장
            with open("api_search_all.json", "w", encoding="utf-8") as f:
                json.dump(res_json, f, ensure_ascii=False, indent=2)

            # json 응답을 미리 정의한 dataclass 타입으로 변환(type-safety)
            webtoon: NWebtoonSearchData = NWebtoonSearchData.from_dict(res_json)

            # 일반 웹툰, 베스트 도전, 도전만화 갯수 파싱
            webtoon_cnt = webtoon.searchWebtoonResult.totalCount
            best_challenge_cnt = webtoon.searchBestChallengeResult.totalCount
            challenge_cnt = webtoon.searchChallengeResult.totalCount

            if (webtoon_cnt + best_challenge_cnt + challenge_cnt) == 0:
                keyword = ""
                while not keyword.strip():
                    keyword = input("검색 결과가 없습니다. 다시 검색해주세요 : ")
                # exit()
            else:
                break

        i = 1

        print("[bold green]-----웹툰 검색결과-----[/bold green]")
        print(f"[상위 5개] ---- 총 {webtoon_cnt}개")
        webtoon_result = self.search_api_parser(webtoon, "webtoon")
        for element in webtoon_result:
            print(f"[bold red]{i}.[/bold red] {element[0]}")
            i += 1

        print("[bold green]-----베스트 도전 검색결과-----[/bold green]")
        print(f"[상위 5개] ---- 총 {best_challenge_cnt}개")
        best_challenge_result = self.search_api_parser(webtoon, "bestChallenge")
        for element in best_challenge_result:
            print(f"[bold red]{i}.[/bold red] {element[0]}")
            i += 1

        print("[bold green]-----도전만화 검색결과-----[/bold green]")
        print(f"[상위 5개] ---- 총 {challenge_cnt}개")
        challenge_result = self.search_api_parser(webtoon, "challenge")
        for element in challenge_result:
            print(f"[bold red]{i}.[/bold red] {element[0]}")
            i += 1

        all_result = (
            webtoon_result + best_challenge_result + challenge_result
        )  # use list comprehension

        msg = ">>> 선택할 웹툰의 번호를 입력해주세요 : "
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

        print("웹툰 이미지 링크를 추출하고, 타이틀 명으로 폴더 생성을 시작합니다...")
        print(
            "너무 오랫동안 지연되거나 멈추면 프로그램을 종료 후 몇초 후 기다렸다가 다시 실행해주세요."
        )
        responses = self.multi_fetch_episode_title(start_index, end_index)

        # print(responses)
        print("데이터 추출이 완료되었습니다.")
        print("추출한 데이터를 변환하고 이미지 다운로드를 시작합니다.")

        # EpisodeResults -> UrlPathListResults 로 변환하기 위해 준비한 리스트
        # 이곳에서 EpisodeResults 에서 UrlPathListResults 로 변환하는 작업이 이루어짐.
        processed_data: UrlPathListResults = []

        img_idx = 0
        for item in responses:
            # 튜플이 비었으면 무시
            if item.title_name != "":
                folder_idx = str(item.no).zfill(
                    self.__settings.get_zero_fill(FileSettingType.Folder)
                )
                folder_title = item.title_name
                img_url_list = item.img_src_list
                for img_url in img_url_list:
                    img_z_fill = str(img_idx).zfill(
                        self.__settings.get_zero_fill(FileSettingType.Image)
                    )
                    img_path = os.path.join(
                        self.__settings.download_path,
                        self.__title,
                        f"[{folder_idx}] {folder_title}",
                        f"{img_z_fill}.jpg",
                    )
                    processed_data.append(UrlPathTuple(img_url, img_path))
                    img_idx += 1
            img_idx = 0

        # 멀티 프로세싱 대신 비동기로 이미지 다운로드 처미
        # 안전성을 위해 아직은 다운로드는 멀티 프로세싱(멀티 쓰레드) 으로 유지함.
        # start = time.time()  # 시작 시간 저장
        # asyncio.run(self.async_multiple_download_images(processed_data))
        # print("비동기 경과 시간 :", time.time() - start)  # 현재시각 - 시작시간 = 실행 시간
        # input()

        # 기존 방식
        # 1. self.get_image_link 에서 이미지 링크를 동기적으로 일괄 추출해서 리스트로 제공하면
        # 2. p_image_download 함수에 병렬적(비동기로 실행)으로 전달되어 다운로드가 처리됨.
        # 3. 결과는 리스트로 반환되는데, 이 리스트는 순서가 보장되지 않음. (by imap_unordered)

        # self.get_image_link 자체는 동기적으로 처리되기 때문에 이때 디렉토리 생성은 순서가 보장되며, 속도를 더 늘리고 싶다면
        # self.get_image_link 함수 역시 병렬 처리로 코드를 변경하면 됨. (not for, but imap_unordered)
        # 아직은 self.get_image_link 은 병렬 처리 하고 있지 않음.
        # 결론적으로 네트워크 I/O에 식한 웹툰 다운로드 속도를 최대한 높이기 위해 이미지 다운로드를 하는 부분 p_image_download 만
        # 병렬적으로 처리되고 있는 것.

        # 새로운 방식
        # 1. self.get_image_link 을 이용하지 않고 새롭게 비동기적인 방식으로 리스트를 가져옴.
        # (함수를 imap_unordered 안에서 호출하지 않고 미리 사전에 데이터를 담은 리스트로 제공)
        # 2. 이후 과정은 동일 p_image_download 함수에서는 병렬적으로 실행되어 이미지 다운로드가 처리됨.
        # 단순히 self.get_image_link 함수를 비동기적 로직으로 개선한 것.
        # 이를 통해 극적인 속도 향상을 얻음.

        # start = time.time()  # 시작 시간 저장
        results: UrlPathListResults = ThreadPool(thread_count).imap_unordered(
            self.p_image_download, processed_data
        )  # type: ignore

        for element in results:
            print(element.img_url, element.path)
        # print("동기 멀티 프로세싱 경과 시간 :", time.time() - start)  # 현재시각 - 시작시간 = 실행 시간
        # input()

    async def async_download_image(self, session, url, path):
        async with session.get(url) as response:
            with open(path, "wb") as f:
                f.write(await response.content.read())
                print(f"{url} 이미지 다운로드 완료")

    async def async_multiple_download_images(self, image_list):
        async with aiohttp.ClientSession() as session:
            tasks = []
            for url, path in image_list:
                tasks.append(
                    asyncio.ensure_future(self.async_download_image(session, url, path))
                )
            await asyncio.gather(*tasks)

    # 웹툰 제목에 맞게 폴더 생성 + 이미지 링크 추출(경로 포함)
    def get_image_link(self, start_index: int, end_index: int) -> list[UrlPathTuple]:
        global download_index

        # 결과값을 저장할 리스트
        result: UrlPathListResults = []
        for i in range(start_index, end_index + 1):
            # fstring으로 변경
            url = f"https://comic.naver.com/{self.__wtype}/detail?titleId={self.__title_id}&no={i}"
            cookies = {"NID_AUT": self.NID_AUT, "NID_SES": self.NID_SES}
            req = requests.get(url, cookies=cookies)
            soup = BeautifulSoup(req.content, "html.parser")

            # 만화가 없는 페이지일 경우 리스트에 추가하지 않음.
            if not soup.select("#subTitle_toolbar"):
                print(
                    f"no={i}가 없습니다. 순번이 존재 하지 않거나 미리보기, 유료화된 페이지입니다. 다운로드 하지 않고 SKIP 합니다."
                )
                continue

            manga_title = soup.select("#subTitle_toolbar")[
                0
            ].get_text()  # 웹툰 제목 가져오기
            manga_title = manga_title.strip()  # 양 끝 공백 제거

            # 리스트를 string 으로 바꾸고 불필요한 string 제거한다.
            manga_title = self.__file_processor.remove_forbidden_str(manga_title)

            # 설정값 읽어오기 (폴더 제로필)
            s = Setting()
            folder_zfill_cnt = s.get_zero_fill(FileSettingType.Folder)

            # 현재 다운로드 인덱스 string으로 변환 후, 제로필(자릿수 0으로 채우기) 적용
            z_fill_idx = str(download_index).zfill(folder_zfill_cnt)
            idx = f"[{z_fill_idx}] "

            directory_title = self.__file_processor.remove_forbidden_str(self.__title)
            img_path = os.path.join(directory_title, idx + manga_title)

            path = img_path

            # download_path 와 path 경로 합치기
            path = os.path.join(self.__settings.download_path, path)

            # print(f'[다운로드 경로] {path}')

            # download_path 폴더 없으면 생성
            if not os.path.exists(self.__settings.download_path):
                os.makedirs(self.__settings.download_path)

            try:
                print(f"[디렉토리 생성] {manga_title}")
                os.makedirs(path)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    print("폴더 생성중 오류가 발생하였습니다")
                    raise

            image_url = soup.select("div.wt_viewer > img")
            j = 0

            s = Setting()
            image_zfill_cnt = s.get_zero_fill(FileSettingType.Image)
            for img in image_url:
                url = str(img["src"])

                parsed = parse.urlparse(url)
                name, ext = os.path.splitext(parsed.path)
                _path = os.path.join(path, str(j).zfill(image_zfill_cnt) + ext)

                if "img-ctguide-white.png" not in url:  # 컷툰이미지 제거하기
                    # URL,PATH 형식으로 List에 저장
                    # Tuple[str, str]를 UrlPath로 변환하여 추가
                    result.append(
                        UrlPathTuple(url, self.__file_processor.remove_tag(_path))
                    )
                j += 1

            download_index += 1
        return result

    # 이미지 링크 추출 동기 버전 - [웹툰 제목에 대한 폴더 생성 & 이미지 링크 추출 + 경로 생성]
    def fetch_episode_title(self, no: int) -> EpisodeUrlTuple:
        url = f"https://comic.naver.com/{self.__wtype}/detail?titleId={self.__title_id}&no={no}"

        # requests를 사용한 동기 방식으로 변경
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        cookies = {"NID_AUT": self.NID_AUT, "NID_SES": self.NID_SES}

        response = requests.get(url, headers=headers, cookies=cookies)
        html: str = response.text

        # id가 subTitle_toolbar인 태그를 찾음.
        pattern = re.compile(
            r'<[^>]*id="subTitle_toolbar"[^>]*>(.*?)</[^>]*>', re.DOTALL
        )

        # HTML 코드에서 패턴을 찾습니다.
        match = pattern.search(html)

        # 매칭된 결과를 가져옵니다.
        if match:
            episode_title = match.group(1).strip()
        else:
            # 제목을 가져오지 못하면 빈 튜플 반환후 종료
            return EpisodeUrlTuple()

        # title 에서 폴더 생성이 불가한 문자 제거
        episode_title = self.__file_processor.remove_forbidden_str(episode_title)

        # exist_ok라는 파라미터를 True로 하면 해당 디렉토리가 기존에 존재하면
        # 에러발생 없이 넘어가고, 없을 경우에만 생성합니다.

        # 다운로드할 메인 폴더 생성
        os.makedirs(self.__settings.download_path, exist_ok=True)

        # 제목에 맞게 폴더 생성 (메인 폴더 안에 들어갈 폴더)
        os.makedirs(
            os.path.join(
                self.__settings.download_path,
                self.__title,
                f"[{no}] {episode_title}",
            ),
            exist_ok=True,
        )

        # id가 sectionContWide 인 태그를 찾음. (img 태그를 묶는 전체 div 태그)
        pattern = re.compile(r'<div.*?id="sectionContWide".*?>(.*?)</div>', re.DOTALL)
        img_srcs = re.findall(pattern, html)

        # 그 안에서 img 태그를 찾아서 src 속성을 가져와 리스트로 저장 (src_list)
        inner_html = img_srcs[0] if img_srcs else ""
        pattern = re.compile(r'<img.*?src="(.*?)".*?>', re.DOTALL)
        img_srcs: list[str] = re.findall(pattern, inner_html)
        return EpisodeUrlTuple(no, episode_title, img_srcs)

    # fetch_episode_title 함수를 동기적으로 순차적으로 실행해서
    # 결과를 받아오는 함수 (실제로 사용하는 함수)

    def multi_fetch_episode_title(
        self, start_index: int, end_index: int
    ) -> EpisodeResults:
        responses: EpisodeResults = []

        # tqdm을 사용하여 진행상황 표시
        for episode in tqdm.tqdm(
            range(start_index, end_index + 1), desc="에피소드 정보 수집"
        ):
            try:
                result = self.fetch_episode_title(episode)
                responses.append(result)
            except Exception as e:
                print(f"에피소드 {episode} 처리 중 오류 발생: {e}")
                # 오류가 발생해도 빈 튜플을 추가하여 인덱스 유지
                responses.append(EpisodeUrlTuple())

        # 결과값 리턴
        return responses

    def set_asyncio_event_loop_policy(self) -> None:
        py_ver = int(f"{sys.version_info.major}{sys.version_info.minor}")
        if py_ver > 37 and sys.platform.startswith("win"):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # 다중 이미지 다운로드

    def p_image_download(self, data: UrlPathTuple) -> UrlPathTuple | None:
        # 다운로드할 이미지가 없으면 빈 리스트를 다시 뱉고 다운로드를 수행하지 않는다.
        if not data:
            return data
        # 참고 : 이미지서버 자체는 로그인 여부 판단안함.
        for i in range(3):  # 총 3회 시도
            try:
                # (URL, PATH) 형태로 들어온 튜플을 읽어냄
                self.image_download(data.img_url, data.path)
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
                with open(self.__settings.error_path, "a") as file:  # append 모드
                    file.write(error)
                    file.close()
                break

    # Getter 함수 구현 (프로퍼티)

    @property
    def title(self) -> str:
        return self.__title

    @property
    def title_id(self) -> str:
        return self.__title_id

    @property
    def content(self) -> str:
        return self.__content

    @property
    def wtype(self) -> WebtoonType:
        return self.__wtype

    @property
    def isadult(self) -> bool:
        return self.__isadult

    @property
    def number(self) -> int:
        return self.__number
