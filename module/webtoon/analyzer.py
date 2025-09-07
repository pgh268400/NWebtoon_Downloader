import asyncio
import aiohttp
import sys
import os
from typing import List, Tuple, Optional
from dataclasses import dataclass

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

# 기존 pydantic 타입 정의 import
from module.headers import headers
from type.api.article_list import NWebtoonArticleListData
from type.api.comic_info import NWebtoonMainData, WebtoonCode
from type.api.webtoon_type import WebtoonType, to_webtoon_type


@dataclass
class EpisodeInfo:
    """에피소드 정보를 담는 데이터 클래스"""

    no: int
    subtitle: str
    thumbnail_lock: bool


@dataclass
class WebtoonMetadata:
    """웹툰 메타데이터를 담는 데이터 클래스"""

    title_id: int
    title_name: str
    synopsis: str
    is_adult: bool
    webtoon_type: WebtoonType
    # list API에서 가져오는 값들 (성인 웹툰일 때는 0)
    total_count: int = 0
    page_size: int = 0
    total_pages: int = 0


class WebtoonAnalyzer:
    """title id를 받아서 웹툰의 정보를 가져오는 클래스"""

    def __init__(
        self,
        title_id: int,
        nid_aut: Optional[str] = None,
        nid_ses: Optional[str] = None,
    ) -> None:
        self.__title_id = title_id

        # API 요청에 사용할 URL
        self.__info_url = "https://comic.naver.com/api/article/list/info"
        self.__list_url = "https://comic.naver.com/api/article/list"

        # 성인 웹툰 접근용 쿠키 설정
        self.__cookies = {}
        if nid_aut and nid_ses:
            self.__cookies = {"NID_AUT": nid_aut, "NID_SES": nid_ses}

        # 멤버 변수 선언 - 실제 데이터는 비동기 함수에서 설정
        self.__title_name = ""
        self.__total_count = 0
        self.__downloadable_count = 0
        self.__page_size = 0
        self.__total_pages = 0
        self.__is_adult = False
        self.__webtoon_type = WebtoonType.webtoon
        self.__synopsis = ""  # 웹툰 설명
        self.__downloadable_episodes: List[EpisodeInfo] = []
        self.__full_episodes: List[EpisodeInfo] = []

    """
    self의 경우 생성된 객체(instance) 를 가르키므로,
    생성자 순서에선 생성된 객체가 없이 설계도 (class) 만 있어서
    @classmethod를 붙여두고 cls(class) 를 활용해서 객체를 초기화 해야 한다고 한다.
    생성자는 기본적으로 동기로 작동하기 때문에 비동기 함수를 활용하기 위해선
    아래와 같은 팩토리 메서드 방식을 사용해야 한다. 
    다른 언어에선 self나 cls 같은 개념이 없어서 그냥 됐던거 같은데 추가적인 학습이 필요해보인다.
    """

    @classmethod
    async def create(
        cls, title_id: int, nid_aut: Optional[str] = None, nid_ses: Optional[str] = None
    ) -> "WebtoonAnalyzer":
        """비동기 팩토리 메서드로 WebtoonAnalyzer 인스턴스를 생성하고 초기화"""
        instance = cls(title_id, nid_aut, nid_ses)  # 여기서 일반생성자 __init__ 실행
        await instance.__initialize()  # 비동기 함수 실행
        return instance

    async def __initialize(self) -> None:
        """웹툰 메타데이터를 가져와 멤버 변수 초기화하는 내부 비동기 함수(메서드)"""

        # 웹툰 메타데이터 가져오기
        metadata: WebtoonMetadata = await self.__fetch_webtoon_metadata()

        # 성인 웹툰이 아닐 때만 에피소드 정보 가져오기
        # 참고 : 성인 웹툰인 경우엔 아래 함수를 통해 에피소드 정보를 가져올 수 없음
        if not metadata.is_adult:
            # 모든 에피소드 정보 가져오기
            all_episodes = await self.__get_all_episodes(metadata)

            # 다운로드 가능한 에피소드 찾기
            downloadable_count, downloadable_episodes = (
                self.__find_downloadable_episodes(all_episodes)
            )
        # 성인 웹툰인 경우 빈 값으로 설정
        else:
            all_episodes = []
            downloadable_count = 0
            downloadable_episodes = []

        # 데이터를 인스턴스 변수에 저장
        self.__title_name = metadata.title_name
        self.__synopsis = metadata.synopsis
        self.__total_count = metadata.total_count
        self.__downloadable_count = downloadable_count
        self.__page_size = metadata.page_size
        self.__total_pages = metadata.total_pages
        self.__is_adult = metadata.is_adult
        self.__webtoon_type = metadata.webtoon_type
        self.__downloadable_episodes = downloadable_episodes
        self.__full_episodes = all_episodes
        self.__title_id = metadata.title_id

    async def __fetch_webtoon_metadata(self) -> WebtoonMetadata:
        """
        웹툰 API 데이터를 활용해 메타데이터를 가져오는 함수

        Returns:
            웹툰 메타데이터 (전체 화수, 페이지 크기, 전체 페이지 수)
        """

        # 웹툰의 정보를 가져오기 위해 info api에 요청한다
        info_url = f"{self.__info_url}?titleId={self.__title_id}"

        # list api 첫 번째 페이지 요청을 활용해 전체 화수, 페이지 크기, 전체 페이지 수를 얻는다.
        list_url = f"{self.__list_url}?titleId={self.__title_id}&page=1"

        async with aiohttp.ClientSession(
            headers=headers, cookies=self.__cookies
        ) as session:
            # info API 요청
            async with session.get(info_url) as info_response:
                if info_response.status != 200:
                    raise Exception(f"Info API 요청 실패: {info_response.status}")

                info_data = await info_response.json()
                comic_info = NWebtoonMainData.from_dict(info_data)

                # 웹툰 설명 가져오기
                synopsis: str = comic_info.synopsis

                # 일반 웹툰 / 베스트도전 / 도전만화 구분 (API 코드 -> 내부 문자열 enum 매핑)
                webtoon_code: WebtoonCode = comic_info.webtoonLevelCode
                webtoon_type: WebtoonType = to_webtoon_type(webtoon_code)

                # 성인 웹툰 여부 확인 (age.type이 RATE_18이면 성인 웹툰)
                is_adult: bool = comic_info.age.type == "RATE_18"

                # 제목 가져오기
                title_name: str = comic_info.titleName

            # list API 요청
            # 성인 웹툰이 아닌 일반 웹툰인 경우
            if not is_adult:
                async with session.get(list_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        # pydantic 모델을 사용하여 데이터 검증
                        article_list_data = NWebtoonArticleListData.from_dict(data)

                        # API 응답에서 실제 값들을 가져옴
                        total_count = article_list_data.totalCount
                        page_size = article_list_data.pageInfo.pageSize
                        total_pages = article_list_data.pageInfo.totalPages
                    else:
                        raise Exception(f"List API 요청 실패: {response.status}")
            # 성인 웹툰인 경우 list 요청은 확정적으로 실패
            else:
                # 성인 웹툰인 경우 list API 요청을 시도하지 않고 0으로 설정
                total_count = 0
                page_size = 0
                total_pages = 0

            return WebtoonMetadata(
                title_id=self.__title_id,
                title_name=title_name,
                synopsis=synopsis,
                is_adult=is_adult,
                webtoon_type=webtoon_type,
                total_count=total_count,
                page_size=page_size,
                total_pages=total_pages,
            )

    async def __get_episode_list_page(self, page: int) -> NWebtoonArticleListData:
        """
        특정 페이지의 에피소드 리스트를 가져오는 함수

        Args:
            page: 페이지 번호

        Returns:
            해당 페이지의 pydantic 모델 데이터
        """
        url = f"{self.__list_url}?titleId={self.__title_id}&page={page}"

        async with aiohttp.ClientSession(
            headers=headers, cookies=self.__cookies
        ) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    # pydantic 모델을 사용하여 데이터 검증 및 변환
                    return NWebtoonArticleListData.from_dict(data)
                else:
                    raise Exception(f"페이지 {page} 요청 실패: {response.status}")

    async def __get_all_episodes(self, metadata: WebtoonMetadata) -> List[EpisodeInfo]:
        """
        모든 에피소드 정보를 가져오는 함수

        Returns:
            모든 에피소드 정보 리스트
        """
        # total_pages가 None이면 에피소드 정보를 가져올 수 없으므로 빈 리스트 반환
        if metadata.total_pages is None:
            return []

        # 모든 페이지를 병렬로 요청 (no=1 ~ no=끝)
        tasks = []
        for page in range(1, metadata.total_pages + 1):
            task = self.__get_episode_list_page(page)
            tasks.append(task)

        # 모든 요청을 동시에 실행
        responses: List[NWebtoonArticleListData] = await asyncio.gather(*tasks)

        # 모든 에피소드 정보를 수집
        all_episodes: list[EpisodeInfo] = []

        for response in responses:
            # pydantic 모델의 articleList에서 에피소드 정보 추출
            for episode in response.articleList:
                episode_info = EpisodeInfo(
                    no=episode.no,
                    subtitle=episode.subtitle,
                    thumbnail_lock=episode.thumbnailLock,
                )
                all_episodes.append(episode_info)

        # no 순으로 오름차순 정렬
        all_episodes.sort(key=lambda x: x.no)

        return all_episodes

    def __find_downloadable_episodes(
        self, episodes: List[EpisodeInfo]
    ) -> Tuple[int, List[EpisodeInfo]]:
        """
        다운로드 가능한 에피소드 수를 찾는 함수

        Args:
            episodes: 정렬된 에피소드 리스트

        Returns:
            (다운로드 가능한 화수, 다운로드 가능한 에피소드 리스트)
        """
        downloadable_episodes = []

        for episode in episodes:
            if episode.thumbnail_lock:
                # thumbnail_lock이 True인 첫 번째 에피소드를 만나면 중단
                break
            downloadable_episodes.append(episode)

        return len(downloadable_episodes), downloadable_episodes

    @property
    def total_count(self) -> int:
        """전체 화수"""
        return self.__total_count

    @property
    def downloadable_count(self) -> int:
        """다운로드 가능한 화수"""
        return self.__downloadable_count

    @property
    def page_size(self) -> int:
        """페이지 크기"""
        return self.__page_size

    @property
    def total_pages(self) -> int:
        """전체 페이지 수"""
        return self.__total_pages

    @property
    def downloadable_episodes(self) -> List[EpisodeInfo]:
        """다운로드 가능한 에피소드 목록"""
        return self.__downloadable_episodes

    @property
    def full_episodes(self) -> List[EpisodeInfo]:
        """전체 에피소드 목록"""
        return self.__full_episodes

    @property
    def title_id(self) -> int:
        "타이틀 id"
        return self.__title_id

    @property
    def title_name(self) -> str:
        """웹툰 제목"""
        return self.__title_name

    @property
    def synopsis(self) -> str:
        """웹툰 설명"""
        return self.__synopsis

    @property
    def is_adult(self) -> bool:
        """성인 웹툰 여부"""
        return self.__is_adult

    @property
    def webtoon_type(self) -> WebtoonType:
        """웹툰 타입 (일반/베스트도전/도전만화)"""
        return self.__webtoon_type

    @property
    def nid_aut(self) -> Optional[str]:
        """NID_AUT 쿠키 값"""
        return self.__cookies.get("NID_AUT")

    @property
    def nid_ses(self) -> Optional[str]:
        """NID_SES 쿠키 값"""
        return self.__cookies.get("NID_SES")


# WebtoonAnalyzer 테스트 함수
async def test_analyzer(title_id: int):
    """WebtoonAnalyzer의 작동을 확인하는 테스트"""
    print(f"\n{'='*50}")

    try:
        analyzer = await WebtoonAnalyzer.create(title_id)
        # pprint(analyzer.__dict__)

        print(f"웹툰명: {analyzer.title_name}")

        # 성인 웹툰 여부 출력
        adult_output = "⭕" if analyzer.is_adult else "❌"
        print(f"- 성인 웹툰: {adult_output}")

        print(f"- 타이틀 id(title_id): {analyzer.title_id}")

        print(f"- 전체 화수 (total_count): {analyzer.total_count}")
        print(
            f"- 다운로드 가능한 화수 (downloadable_count): {analyzer.downloadable_count}"
        )
        print(f"- 페이지 크기 (page_size): {analyzer.page_size}")
        print(f"- 전체 페이지 수 (total_pages): {analyzer.total_pages}")
        print(f"- 전체 에피소드 수 (full_episodes): {len(analyzer.full_episodes)}")

        # 이 값은 downloadable_count 와 무조건 같아야 한다.
        print(
            f"- 다운로드 가능한 에피소드 수 (downloadable_episodes): {len(analyzer.downloadable_episodes)}"
        )

        # 전체 에피소드 출력
        print("\n전체 에피소드 (처음 5개):")
        for episode in analyzer.full_episodes[:5]:
            lock_status = "🔒" if episode.thumbnail_lock else "🔓"
            print(f"  {episode.no}화: {episode.subtitle} {lock_status}")

        print("\n전체 에피소드 (마지막 5개):")
        for episode in analyzer.full_episodes[-5:]:
            lock_status = "🔒" if episode.thumbnail_lock else "🔓"
            print(f"  {episode.no}화: {episode.subtitle} {lock_status}")

        # 다운로드 가능한 에피소드 출력
        print("\n다운로드 가능한 에피소드 (처음 5개):")
        for episode in analyzer.downloadable_episodes[:5]:
            lock_status = "🔒" if episode.thumbnail_lock else "🔓"
            print(f"  {episode.no}화: {episode.subtitle} {lock_status}")

        print("\n다운로드 가능한 에피소드 (마지막 5개):")
        for episode in analyzer.downloadable_episodes[-5:]:
            lock_status = "🔒" if episode.thumbnail_lock else "🔓"
            print(f"  {episode.no}화: {episode.subtitle} {lock_status}")

        # 전체 에피소드에서 잠금 에피소드들 출력
        locked_episodes = [ep for ep in analyzer.full_episodes if ep.thumbnail_lock]
        if locked_episodes:
            print(f"\n🔒 잠금 에피소드 ({len(locked_episodes)}개):")
            for episode in locked_episodes[:10]:  # 처음 10개만 출력
                print(f"  {episode.no}화: {episode.subtitle} 🔒")
            if len(locked_episodes) > 10:
                print(f"  ... 및 {len(locked_episodes) - 10}개 더")

    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback

        traceback.print_exc()


# WebtoonAnalyzer 테스트 메인 함수
async def test_case():
    """WebtoonAnalyzer 테스트 - 지정된 title ID들로 테스트"""
    print("WebtoonAnalyzer 테스트 시작")

    # 테스트할 title ID들 - 일반 / 베도 / 도전 웹툰, 성인 웹툰 X
    title_ids: list[int] = [835801, 183559, 602287, 842399, 841764, 483237]

    for title_id in title_ids:
        await test_analyzer(title_id)

    print(f"\n{'=' * 50}")


if __name__ == "__main__":
    # WebtoonAnalyzer 객체 테스트
    asyncio.run(test_case())
