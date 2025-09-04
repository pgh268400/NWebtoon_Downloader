import asyncio
from pprint import pprint
import aiohttp
import sys
import os
import time
from typing import List, Tuple
from dataclasses import dataclass
from bs4 import BeautifulSoup

# 상위 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 기존 pydantic 타입 정의 import
from module.headers import headers
from type.api.article_list import NWebtoonArticleListData
from type.api.comic_info import NWebtoonMainData


@dataclass
class EpisodeInfo:
    """에피소드 정보를 담는 데이터 클래스"""

    no: int
    subtitle: str
    thumbnail_lock: bool
    img_urls: List[str] = None  # type: ignore

    def __post_init__(self):
        if self.img_urls is None:
            self.img_urls = []


@dataclass
class WebtoonMetadata:
    """웹툰 메타데이터를 담는 데이터 클래스"""

    title_id: int
    title_name: str
    is_adult: bool
    total_count: int
    page_size: int
    total_pages: int


class WebtoonAnalyzer:
    """title id를 받아서 웹툰의 정보를 가져오는 클래스"""

    def __init__(self, title_id: int) -> None:
        self.__title_id = title_id
        self.__info_url = "https://comic.naver.com/api/article/list/info"
        self.__list_url = "https://comic.naver.com/api/article/list"

        # 기본값 선언 - 실제 데이터는 비동기 함수에서 설정됨
        self.__total_count = 0
        self.__downloadable_count = 0
        self.__page_size = 0
        self.__total_pages = 0
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
    async def create(cls, title_id: int) -> "WebtoonAnalyzer":
        """비동기 팩토리 메서드로 WebtoonAnalyzer 인스턴스를 생성하고 초기화"""
        instance = cls(title_id)  # 여기서 일반생성자 __init__ 실행
        await instance.__init_analysis()
        return instance

    async def __init_analysis(self) -> None:
        """분석 결과를 초기화하는 내부 메서드"""
        # 웹툰 메타데이터 가져오기
        metadata: WebtoonMetadata = await self.__fetch_webtoon_metadata()

        # 모든 에피소드 정보 가져오기
        all_episodes = await self.__get_all_episodes(metadata)

        # 다운로드 가능한 에피소드 찾기
        downloadable_count, downloadable_episodes = self.__find_downloadable_episodes(
            all_episodes
        )

        # 데이터를 인스턴스 변수에 저장
        self.__total_count = metadata.total_count
        self.__downloadable_count = downloadable_count
        self.__page_size = metadata.page_size
        self.__total_pages = metadata.total_pages
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

        async with aiohttp.ClientSession(headers=headers) as session:
            # info API 요청
            async with session.get(info_url) as info_response:
                if info_response.status != 200:
                    raise Exception(f"Info API 요청 실패: {info_response.status}")

                info_data = await info_response.json()
                comic_info = NWebtoonMainData.from_dict(info_data)

                # 성인 웹툰 여부 확인 (age.type이 RATE_18이면 성인 웹툰)
                is_adult = comic_info.age.type == "RATE_18"

                # 제목 가져오기
                title_name = comic_info.titleName

            # list API 요청
            async with session.get(list_url) as response:
                # HTTP 요청에 성공한 경우
                if response.status == 200:
                    data = await response.json()
                    # pydantic 모델을 사용하여 데이터 검증
                    article_list_data = NWebtoonArticleListData.from_dict(data)

                    # API 응답에서 실제 값들을 가져옴
                    total_count = article_list_data.totalCount
                    page_size = article_list_data.pageInfo.pageSize
                    total_pages = article_list_data.pageInfo.totalPages

                    return WebtoonMetadata(
                        title_id=self.__title_id,
                        title_name=title_name,
                        is_adult=is_adult,
                        total_count=total_count,
                        page_size=page_size,
                        total_pages=total_pages,
                    )
                else:
                    raise Exception(f"List API 요청 실패: {response.status}")

    async def __get_episode_list_page(self, page: int) -> NWebtoonArticleListData:
        """
        특정 페이지의 에피소드 리스트를 가져오는 함수

        Args:
            page: 페이지 번호

        Returns:
            해당 페이지의 pydantic 모델 데이터
        """
        url = f"{self.__list_url}?titleId={self.__title_id}&page={page}"

        async with aiohttp.ClientSession(headers=headers) as session:
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

        print(metadata)
        print(
            f"  메타데이터: 전체 {metadata.total_count}화, 페이지당 {metadata.page_size}화, 총 {metadata.total_pages}페이지"
        )

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


class WebtoonDownloader:
    """웹툰 다운로드 관련 기능을 담당하는 클래스"""

    def __init__(self, title_id: int) -> None:
        self.__title_id = title_id
        self.__detail_url = "https://comic.naver.com/webtoon/detail"

    async def get_episode_images(self, episode: EpisodeInfo) -> EpisodeInfo:
        """
        특정 에피소드의 이미지 URL들을 가져오는 함수

        Args:
            episode: 에피소드 정보

        Returns:
            이미지 URL이 추가된 에피소드 정보
        """
        url = f"{self.__detail_url}?titleId={self.__title_id}&no={episode.no}"

        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        # HTML 내용 가져오기 시간 측정
                        html_start_time = time.time()
                        html_content = await response.text()
                        html_end_time = time.time()
                        html_time = html_end_time - html_start_time

                        # BeautifulSoup 파싱 시간 측정
                        parse_start_time = time.time()
                        soup = BeautifulSoup(html_content, "lxml")

                        # sectionContWide 태그 안의 모든 img 태그 찾기
                        section = soup.find("div", id="sectionContWide")
                        if section:
                            img_tags = section.find_all("img")  # type: ignore
                            img_urls = []

                            for img in img_tags:
                                src = img.get("src")  # type: ignore
                                if src:
                                    img_urls.append(src)
                        else:
                            img_urls = []

                        parse_end_time = time.time()
                        parse_time = parse_end_time - parse_start_time
                        total_parse_time = parse_end_time - html_start_time

                        episode.img_urls = img_urls
                        print(
                            f"  {episode.no}화: {len(img_urls)}개 이미지 URL 수집 완료 (HTML: {html_time:.3f}s, 파싱: {parse_time:.3f}s, 총: {total_parse_time:.3f}s)"
                        )
                    else:
                        print(f"  {episode.no}화: HTTP 요청 실패 ({response.status})")
                        episode.img_urls = []
        except Exception as e:
            print(f"  {episode.no}화: 이미지 URL 수집 중 오류 발생 - {e}")
            episode.img_urls = []

        return episode

    async def get_episodes_with_images(
        self, episodes: List[EpisodeInfo]
    ) -> List[EpisodeInfo]:
        """
        에피소드들의 이미지 URL을 모두 가져오는 함수

        Args:
            episodes: 이미지 URL을 수집할 에피소드 리스트

        Returns:
            이미지 URL이 포함된 에피소드 리스트
        """
        if not episodes:
            print("수집할 에피소드가 없습니다.")
            return []

        print(f"\n{len(episodes)}개 에피소드의 이미지 URL을 수집합니다...")

        # 모든 에피소드의 이미지 URL을 병렬로 가져오기
        tasks = []
        for episode in episodes:
            task = self.get_episode_images(episode)
            tasks.append(task)

        # 모든 요청을 동시에 실행
        episodes_with_images = await asyncio.gather(*tasks)

        print(f"\n총 {len(episodes_with_images)}개 에피소드의 이미지 URL 수집 완료!")

        return episodes_with_images

    async def get_episodes_with_images_batch(
        self, episodes: List[EpisodeInfo], batch_size: int
    ) -> List[EpisodeInfo]:
        """
        에피소드들의 이미지 URL을 배치 단위로 가져오는 함수

        Args:
            episodes: 이미지 URL을 수집할 에피소드 리스트
            batch_size: 한 번에 처리할 에피소드 수

        Returns:
            이미지 URL이 포함된 에피소드 리스트
        """
        if not episodes:
            print("수집할 에피소드가 없습니다.")
            return []

        print(f"\n{len(episodes)}개 에피소드의 이미지 URL을 수집합니다...")
        print(f"배치 크기: {batch_size}개씩 처리")

        episodes_with_images = []
        total_episodes = len(episodes)

        # 배치 단위로 처리
        for i in range(0, total_episodes, batch_size):
            batch = episodes[i : i + batch_size]
            print(
                f"\n배치 {i//batch_size + 1}/{(total_episodes + batch_size - 1)//batch_size} 처리 중... ({i+1}~{min(i+batch_size, total_episodes)}화)"
            )

            # 현재 배치의 이미지 URL을 병렬로 가져오기
            tasks = []
            for episode in batch:
                task = self.get_episode_images(episode)
                tasks.append(task)

            # 현재 배치의 요청을 동시에 실행
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # 결과 처리
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    print(f"  {batch[j].no}화: 오류 발생 - {result}")
                    batch[j].img_urls = []
                    episodes_with_images.append(batch[j])
                else:
                    episodes_with_images.append(result)

            # 서버 부하 방지를 위한 잠시 대기
            if i + batch_size < total_episodes:
                print("  서버 부하 방지를 위해 1초 대기합니다.")
                await asyncio.sleep(1)

        print(f"\n총 {len(episodes_with_images)}개 에피소드의 이미지 URL 수집 완료!")

        return episodes_with_images

    async def download_episode_images(self, episode: EpisodeInfo) -> bool:
        """
        특정 에피소드의 이미지를 다운로드하는 함수

        Args:
            episode: 이미지 URL이 포함된 에피소드 정보

        Returns:
            다운로드 성공 여부
        """
        if not hasattr(episode, "img_urls") or not episode.img_urls:
            print(f"  {episode.no}화: 다운로드할 이미지 URL이 없습니다.")
            return False

        try:
            print(f"  {episode.no}화 '{episode.subtitle}' 다운로드 시작...")
            print(f"    총 {len(episode.img_urls)}개 이미지 다운로드 예정")

            # TODO: 실제 이미지 다운로드 로직 구현
            # 여기서는 현재 이미지 URL 수집만 완료된 상태를 표시
            print(f"    다운로드 준비 완료 (실제 다운로드 로직은 별도 구현 필요)")

            return True
        except Exception as e:
            print(f"  {episode.no}화: 다운로드 중 오류 발생 - {e}")
            return False

    async def download_episodes(self, episodes: List[EpisodeInfo]) -> List[bool]:
        """
        에피소드들의 이미지를 모두 다운로드하는 함수

        Args:
            episodes: 이미지 URL이 포함된 에피소드 리스트

        Returns:
            각 에피소드의 다운로드 성공 여부 리스트
        """
        if not episodes:
            print("다운로드할 에피소드가 없습니다.")
            return []

        print(f"\n{len(episodes)}개 에피소드의 이미지를 다운로드합니다...")

        # 모든 에피소드의 이미지를 병렬로 다운로드
        tasks = []
        for episode in episodes:
            task = self.download_episode_images(episode)
            tasks.append(task)

        # 모든 요청을 동시에 실행
        download_results = await asyncio.gather(*tasks)

        success_count = sum(download_results)
        print(f"\n총 {len(episodes)}개 에피소드 중 {success_count}개 다운로드 완료!")

        return download_results

    async def download_episodes_batch(
        self, episodes: List[EpisodeInfo], batch_size: int
    ) -> List[bool]:
        """
        에피소드들의 이미지를 배치 단위로 다운로드하는 함수

        Args:
            episodes: 이미지 URL이 포함된 에피소드 리스트
            batch_size: 한 번에 처리할 에피소드 수

        Returns:
            각 에피소드의 다운로드 성공 여부 리스트
        """
        if not episodes:
            print("다운로드할 에피소드가 없습니다.")
            return []

        print(f"\n{len(episodes)}개 에피소드의 이미지를 다운로드합니다...")
        print(f"배치 크기: {batch_size}개씩 처리")

        download_results = []
        total_episodes = len(episodes)

        # 배치 단위로 처리
        for i in range(0, total_episodes, batch_size):
            batch = episodes[i : i + batch_size]
            print(
                f"\n배치 {i//batch_size + 1}/{(total_episodes + batch_size - 1)//batch_size} 처리 중... ({i+1}~{min(i+batch_size, total_episodes)}화)"
            )

            # 현재 배치의 이미지를 병렬로 다운로드
            tasks = []
            for episode in batch:
                task = self.download_episode_images(episode)
                tasks.append(task)

            # 현재 배치의 요청을 동시에 실행
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # 결과 처리
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    print(f"  {batch[j].no}화: 오류 발생 - {result}")
                    download_results.append(False)
                else:
                    download_results.append(result)

            # 서버 부하 방지를 위한 잠시 대기
            if i + batch_size < total_episodes:
                print("  서버 부하 방지를 위해 1초 대기합니다.")
                await asyncio.sleep(1)

        success_count = sum(download_results)
        print(f"\n총 {len(episodes)}개 에피소드 중 {success_count}개 다운로드 완료!")

        return download_results

    @property
    def title_id(self) -> int:
        """타이틀 id"""
        return self.__title_id


# 통합 테스트 함수
async def test_webtoon(title_id: int, webtoon_name: str):
    """웹툰 분석 테스트 함수"""
    print("\n" + "=" * 60)
    print(f"테스트: {webtoon_name} (titleId: {title_id})")
    print("=" * 60)

    analyzer = await WebtoonAnalyzer.create(title_id)

    try:
        # 전체 분석 테스트
        print("전체 웹툰 분석 테스트...")

        # 프로퍼티를 통해 데이터 접근
        total_count = analyzer.total_count
        downloadable_count = analyzer.downloadable_count
        full_episodes = analyzer.full_episodes
        downloadable_episodes = analyzer.downloadable_episodes

        print(f"   전체 화수: {total_count}")
        print(f"   다운로드 가능한 화수: {downloadable_count}")
        print(f"   전체 에피소드 수: {len(full_episodes)}")
        print(f"   다운로드 가능한 에피소드 수: {len(downloadable_episodes)}")

        # 전체 에피소드 출력
        print("\n전체 에피소드 (처음 5개):")
        for episode in full_episodes[:5]:
            lock_status = "🔒" if episode.thumbnail_lock else "🔓"
            print(f"  {episode.no}화: {episode.subtitle} {lock_status}")

        print("\n전체 에피소드 (마지막 5개):")
        for episode in full_episodes[-5:]:
            lock_status = "🔒" if episode.thumbnail_lock else "🔓"
            print(f"  {episode.no}화: {episode.subtitle} {lock_status}")

        # 다운로드 가능한 에피소드 출력
        print("\n다운로드 가능한 에피소드 (처음 5개):")
        for episode in downloadable_episodes[:5]:
            lock_status = "🔒" if episode.thumbnail_lock else "🔓"
            print(f"  {episode.no}화: {episode.subtitle} {lock_status}")

        print("\n다운로드 가능한 에피소드 (마지막 5개):")
        for episode in downloadable_episodes[-5:]:
            lock_status = "🔒" if episode.thumbnail_lock else "🔓"
            print(f"  {episode.no}화: {episode.subtitle} {lock_status}")

        # 전체 에피소드에서 잠금 에피소드들 출력
        locked_episodes = [ep for ep in full_episodes if ep.thumbnail_lock]
        if locked_episodes:
            print(f"\n잠금 에피소드 목록 ({len(locked_episodes)}개):")
            for episode in locked_episodes:
                print(f"  {episode.no}화: {episode.subtitle}")

        # 요약 정보
        print("\n요약:")
        print(f"  전체 화수: {total_count}")
        print(f"  다운로드 가능: {downloadable_count}화")
        print(f"  잠금 상태: {len(locked_episodes)}화")
        print(f"  다운로드 가능 비율: {downloadable_count/len(full_episodes)*100:.1f}%")

    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback

        traceback.print_exc()


# 이미지 URL 수집 테스트 함수
async def test_image_collection(
    title_id: int, webtoon_name: str, max_episodes: int = 3
):
    """이미지 URL 수집 테스트 함수"""
    print("\n" + "=" * 60)
    print(f"이미지 URL 수집 테스트: {webtoon_name} (titleId: {title_id})")
    print("=" * 60)

    analyzer = await WebtoonAnalyzer.create(title_id)
    downloader = WebtoonDownloader(title_id)

    try:
        # 다운로드 가능한 에피소드 가져오기
        downloadable_episodes = analyzer.downloadable_episodes

        if not downloadable_episodes:
            print("다운로드 가능한 에피소드가 없습니다.")
            return

        # 테스트용으로 처음 몇 개 에피소드만 선택
        test_episodes = downloadable_episodes[:max_episodes]
        print(f"테스트할 에피소드 수: {len(test_episodes)}개")

        # 각 에피소드의 이미지 URL 수집
        for episode in test_episodes:
            print(f"\n{episode.no}화 '{episode.subtitle}' 이미지 URL 수집 중...")
            episode_with_images = await downloader.get_episode_images(episode)

            print(f"  수집된 이미지 URL 수: {len(episode_with_images.img_urls)}")
            if episode_with_images.img_urls:
                print("  첫 번째 이미지 URL:")
                print(f"    {episode_with_images.img_urls[0]}")
                if len(episode_with_images.img_urls) > 1:
                    print("  마지막 이미지 URL:")
                    print(f"    {episode_with_images.img_urls[-1]}")

    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback

        traceback.print_exc()


# 메인 테스트 함수
async def main():
    """웹툰 분석기 테스트 - 여러 웹툰으로 테스트"""
    print("웹툰 분석기 테스트 시작")
    print("pydantic 타입 정의를 활용한 버전 (API 응답 기반 pageSize 사용)")

    # 테스트할 웹툰 목록
    test_webtoons = [
        (717481, "일렉시드"),
        (842399, "슬램덩크(SLAM DUNK)"),
        (183559, "신의 탑"),
    ]

    # 여러 테스트 케이스 실행
    for title_id, webtoon_name in test_webtoons:
        await test_webtoon(title_id, webtoon_name)

    print("\n" + "=" * 60)
    print("모든 테스트 완료!")
    print("=" * 60)


# 이미지 수집 메인 함수
async def main_image_collection():
    """이미지 URL 수집 테스트"""
    print("이미지 URL 수집 테스트 시작")

    # 테스트할 웹툰 (신의 탑으로 테스트)
    title_id = 183559
    webtoon_name = "신의 탑"

    await test_image_collection(title_id, webtoon_name, max_episodes=3)

    print("\n" + "=" * 60)
    print("이미지 URL 수집 테스트 완료!")
    print("=" * 60)


# 전체 이미지 수집 테스트 함수
async def test_full_image_collection(title_id: int, webtoon_name: str):
    """전체 다운로드 가능한 에피소드의 이미지 URL을 한 번에 수집하는 테스트"""
    print("\n" + "=" * 60)
    print(f"전체 이미지 URL 수집 테스트: {webtoon_name} (titleId: {title_id})")
    print("=" * 60)

    analyzer = await WebtoonAnalyzer.create(title_id)
    downloader = WebtoonDownloader(title_id)

    try:
        # 다운로드 가능한 에피소드 가져오기
        downloadable_episodes = analyzer.downloadable_episodes

        if not downloadable_episodes:
            print("다운로드 가능한 에피소드가 없습니다.")
            return

        # 테스트용으로 처음 5개 에피소드만 선택하여 개별 처리
        test_episodes = downloadable_episodes[:5]
        print(f"테스트할 에피소드 수: {len(test_episodes)}개 (처음 5개만)")

        episodes_with_images = []

        # 각 에피소드를 개별적으로 처리
        for episode in test_episodes:
            print(f"\n{episode.no}화 '{episode.subtitle}' 이미지 URL 수집 중...")
            episode_with_images = await downloader.get_episode_images(episode)
            episodes_with_images.append(episode_with_images)

            print(f"  수집된 이미지 URL 수: {len(episode_with_images.img_urls)}")
            if episode_with_images.img_urls:
                print("  첫 번째 이미지 URL:")
                print(f"    {episode_with_images.img_urls[0]}")

        print(f"\n총 {len(episodes_with_images)}개 에피소드의 이미지 URL 수집 완료!")

        # 결과 요약
        total_images = 0
        for episode in episodes_with_images:
            total_images += len(episode.img_urls)
            print(
                f"  {episode.no}화 '{episode.subtitle}': {len(episode.img_urls)}개 이미지"
            )

        print(f"\n총 이미지 URL 수: {total_images}개")

    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback

        traceback.print_exc()


# 전체 이미지 수집 메인 함수
async def main_full_image_collection():
    """전체 이미지 URL 수집 테스트"""
    print("전체 이미지 URL 수집 테스트 시작")

    # 테스트할 웹툰 (신의 탑으로 테스트)
    title_id = 183559
    webtoon_name = "신의 탑"

    await test_full_image_collection(title_id, webtoon_name)

    print("\n" + "=" * 60)
    print("전체 이미지 URL 수집 테스트 완료!")
    print("=" * 60)


# 배치 처리 이미지 수집 테스트 함수
async def test_batch_image_collection(title_id: int, webtoon_name: str):
    """배치 처리로 이미지 URL을 수집하는 테스트"""
    print("\n" + "=" * 60)
    print(f"배치 처리 이미지 URL 수집 테스트: {webtoon_name} (titleId: {title_id})")
    print("=" * 60)

    analyzer = await WebtoonAnalyzer.create(title_id)
    downloader = WebtoonDownloader(title_id)


    try:
        # 다운로드 가능한 에피소드 가져오기
        downloadable_episodes = analyzer.downloadable_episodes

        if not downloadable_episodes:
            print("다운로드 가능한 에피소드가 없습니다.")
            return

        # 테스트용으로 처음 10개 에피소드만 선택
        test_episodes = downloadable_episodes[:10]
        print(f"테스트할 에피소드 수: {len(test_episodes)}개 (처음 10개만)")

        # 배치 크기 설정하고 이미지 URL 수집
        episodes_with_images = await downloader.get_episodes_with_images_batch(
            test_episodes, batch_size=5
        )

        print(f"\n총 {len(episodes_with_images)}개 에피소드의 이미지 URL 수집 완료!")

        # 결과 요약
        total_images = 0
        for episode in episodes_with_images:
            total_images += len(episode.img_urls)
            print(
                f"  {episode.no}화 '{episode.subtitle}': {len(episode.img_urls)}개 이미지"
            )

        print(f"\n총 이미지 URL 수: {total_images}개")

    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback

        traceback.print_exc()


# 배치 처리 메인 함수
async def main_batch_image_collection():
    """배치 처리 이미지 URL 수집 테스트"""
    print("배치 처리 이미지 URL 수집 테스트 시작")

    # 테스트할 웹툰 (신의 탑으로 테스트)
    title_id = 183559
    webtoon_name = "신의 탑"

    await test_batch_image_collection(title_id, webtoon_name)

    print("\n" + "=" * 60)
    print("배치 처리 이미지 URL 수집 테스트 완료!")
    print("=" * 60)


if __name__ == "__main__":
    # 기본 테스트 실행
    # asyncio.run(main())

    # 이미지 수집 테스트 실행
    # asyncio.run(main_image_collection())

    # 전체 이미지 수집 테스트 실행
    # asyncio.run(main_full_image_collection())

    # 배치 처리 이미지 수집 테스트 실행
    asyncio.run(main_batch_image_collection())
