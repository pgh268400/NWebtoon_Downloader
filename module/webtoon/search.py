import json
import os
import re
from typing import List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.box import ROUNDED
import requests

# 경로는 main.py의 위치를 기준으로 import함에 주의
from module.headers import headers
from type.api.search_all import NWebtoonSearchData, SearchGenre, SearchView
from type.api.webtoon_type import WebtoonType


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

        # 5~6자리의 숫자를 찾는 정규식
        exp = "[0-9]{5,6}"
        if "titleId=" in query:  # 입력값에 title_id가 존재하면 title_id 패턴 검색
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
        type: WebtoonType,
    ):
        if type == WebtoonType.webtoon:
            webtoon_lst = webtoon.searchWebtoonResult.searchViewList
        elif type == WebtoonType.bestChallenge:
            webtoon_lst = webtoon.searchBestChallengeResult.searchViewList
        elif type == WebtoonType.challenge:
            webtoon_lst = webtoon.searchChallengeResult.searchViewList

        result = []
        for search_view in webtoon_lst:
            # 검색 결과를 담고 있는 SearchView 객체
            search_view: SearchView

            # SearchView 객체에서 필요한 정보만 가져온다.
            title_name: str = search_view.titleName  # 웹툰 제목
            display_author: str = search_view.displayAuthor  # 작가
            genre_list: List[SearchGenre] = search_view.genreList  # 장르
            article_total_count: int = search_view.articleTotalCount  # 총 화수
            last_article_service_date: str = (
                search_view.lastArticleServiceDate
            )  # 마지막 업데이트 날짜
            synopsis: str = search_view.synopsis  # 웹툰 설명

            genre_names = [genre.description for genre in genre_list]

            # 테이블 컬럼 형태로 보여주기 위해 구조화하여 반환한다.
            result.append(
                {
                    "title_name": title_name,
                    "display_author": display_author,
                    "genres": " / ".join(genre_names),
                    "article_total_count": article_total_count,
                    "last_article_service_date": last_article_service_date,
                    "synopsis": synopsis,
                    "title_id": search_view.titleId,
                }
            )

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

        # Rich 콘솔과 패널/테이블을 이용하여 예쁘게 출력
        console = Console()

        # 테이블 렌더링 시작 시 이전 콘솔 내용을 모두 지우기
        # console.clear()
        os.system("cls" if os.name == "nt" else "clear")

        def render_section(
            title: str, total_count: int, results: list[dict], start_idx: int
        ) -> int:
            """섹션별 결과를 테이블로 렌더링하고 다음 시작 인덱스를 반환한다."""
            table = Table(
                show_header=True, header_style="bold cyan", box=ROUNDED, expand=True
            )
            table.add_column("No", style="bold magenta", width=4, no_wrap=True)
            table.add_column(
                "제목",
                style="white",
                no_wrap=False,
                overflow="fold",
                min_width=16,
            )
            table.add_column(
                "글/그림",
                style="white",
                no_wrap=False,
                overflow="fold",
                min_width=10,
            )
            table.add_column(
                "장르",
                style="white",
                no_wrap=False,
                overflow="fold",
                min_width=18,
            )
            table.add_column(
                "총 화수", style="white", justify="right", width=6, no_wrap=True
            )
            table.add_column("최종 업데이트", style="white", width=12, no_wrap=True)

            idx = start_idx
            for element in results:
                # element 는 search_api_parser 에서 구조화한 dict
                table.add_row(
                    f"{idx}",
                    element["title_name"],
                    element["display_author"],
                    (element["genres"] if element["genres"] else "-"),
                    f"{element['article_total_count']}",
                    element["last_article_service_date"],
                )
                idx += 1

            panel = Panel(
                table,
                title=f"[bold green]{title}[/bold green]",
                subtitle=f"[dim]상위 5개 · 총 {total_count}개[/dim]",
                border_style="green",
                padding=(1, 2),
                expand=True,
            )
            # 섹션 간 가독성을 위해 한 줄 띄어쓰기
            console.print()
            console.print(panel)
            return idx

        # 결과 파싱
        webtoon_result = self.search_api_parser(webtoon, WebtoonType.webtoon)
        best_challenge_result = self.search_api_parser(
            webtoon, WebtoonType.bestChallenge
        )
        challenge_result = self.search_api_parser(webtoon, WebtoonType.challenge)

        # 섹션 별 출력 (인덱스 증가 유지)
        i = render_section("웹툰 검색결과", webtoon_cnt, webtoon_result, i)
        i = render_section(
            "베스트 도전 검색결과", best_challenge_cnt, best_challenge_result, i
        )
        i = render_section("도전만화 검색결과", challenge_cnt, challenge_result, i)

        all_result = (
            webtoon_result + best_challenge_result + challenge_result
        )  # list comprehension 사용

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

        title_id = str(all_result[index - 1]["title_id"])
        # print(f'선택한 웹툰의 title_id : {title_id}')
        return title_id

    @property
    def title_id(self) -> int:
        return int(self.__title_id)
