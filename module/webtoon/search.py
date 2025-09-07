import json
import re
from typing import Literal
from rich import print
import requests

# 경로는 main.py의 위치를 기준으로 import함에 주의
from module.headers import headers
from type.api.search_all import NWebtoonSearchData, SearchView


class WebtoonSearch:
    def __init__(self, query: str) -> None:
        """
        검색어를 주고 객체를 생성하면 이 생성자에서 처리를 합니다.
        검색어 제공시 해당 객체가 알아서 검색창을 띄어주고 사용자가 선택한 웹툰에 따라 웹툰 id(title_id) 를 가질 수 있게 합니다.

        Args:
            query (str): 검색어 (또는 웹툰 TITLE ID, URL 이 될 수도 있음)
        """

        # 생성자에서 파이썬 인스턴스 변수 초기화
        self.__title_id: str = ""

        exp = "[0-9]{5,6}"
        if "titleId=" in query:  # 입력값에 titleid가 존재하면
            id_pattern = re.search(exp, query)
            if id_pattern:
                self.__title_id = id_pattern.group()
            else:
                raise ValueError(
                    "Error : titleid는 5~6자리의 숫자입니다. 입력값을 확인해주세요."
                )
        else:
            input_is_id = re.match(exp, query)  # 문자열 시작부터 매칭
            if input_is_id:
                self.__title_id = query  # 입력값 자체가 ID
            else:  # 검색어면
                self.__title_id = self.search(query)

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

            # json 응답을 미리 정의한 dataclass 타입으로 변환(type-safety)
            webtoon: NWebtoonSearchData = NWebtoonSearchData.from_dict(res_json)

            # 일반 웹툰, 베스트 도전, 도전만화 갯수 파싱
            webtoon_cnt: int = webtoon.searchWebtoonResult.totalCount
            best_challenge_cnt: int = webtoon.searchBestChallengeResult.totalCount
            challenge_cnt: int = webtoon.searchChallengeResult.totalCount

            if (webtoon_cnt + best_challenge_cnt + challenge_cnt) == 0:
                keyword = ""
                while not keyword.strip():
                    keyword = input("검색 결과가 없습니다. 다시 검색해주세요 : ")
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

    @property
    def title_id(self) -> int:
        return int(self.__title_id)
