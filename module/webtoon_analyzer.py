import asyncio
from pprint import pprint
import aiohttp
import sys
import os
from typing import List, Tuple
from dataclasses import dataclass

# 상위 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 기존 pydantic 타입 정의 import
from module.headers import headers
from type.api.article_list import NWebtoonArticleListData


@dataclass
class EpisodeInfo:
    """에피소드 정보를 담는 데이터 클래스"""

    no: int
    subtitle: str
    thumbnail_lock: bool


@dataclass
class WebtoonAnalysis:
    """웹툰 분석 결과를 담는 데이터 클래스"""

    total_count: int
    downloadable_count: int
    page_size: int
    total_pages: int
    downloadable_episodes: List[EpisodeInfo]
    full_episodes: List[EpisodeInfo]


@dataclass
class WebtoonMetadata:
    """웹툰 메타데이터를 담는 데이터 클래스"""

    title_id: int
    total_count: int
    page_size: int
    total_pages: int


class WebtoonAnalyzer:
    """웹툰 분석기 클래스"""

    def __init__(self, title_id: int) -> None:
        self.__title_id = title_id
        self.__base_url = "https://comic.naver.com/api/article/list"

    async def __fetch_webtoon_metadata(self) -> WebtoonMetadata:
        """
        웹툰 글 목록 첫 페이지 API 데이터를 활용해 메타데이터를 가져오는 함수 (첫 번째 페이지 요청)

        Returns:
            웹툰 메타데이터 (전체 화수, 페이지 크기, 전체 페이지 수)
        """
        url = f"{self.__base_url}?titleId={self.__title_id}&page=1"

        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url) as response:
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
                        total_count=total_count,
                        page_size=page_size,
                        total_pages=total_pages,
                    )
                else:
                    raise Exception(f"API 요청 실패: {response.status}")

    async def get_episode_list_page(self, page: int) -> NWebtoonArticleListData:
        """
        특정 페이지의 에피소드 리스트를 가져오는 함수

        Args:
            page: 페이지 번호

        Returns:
            해당 페이지의 pydantic 모델 데이터
        """
        url = f"{self.__base_url}?titleId={self.__title_id}&page={page}"

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
            task = self.get_episode_list_page(page)
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

    async def analyze_webtoon(self) -> WebtoonAnalysis:
        """
        웹툰 정보를 분석하는 메인 함수

        Returns:
            웹툰 분석 결과
        """
        # 웹툰 메타데이터 가져오기
        metadata: WebtoonMetadata = await self.__fetch_webtoon_metadata()

        # 모든 에피소드 정보 가져오기
        all_episodes = await self.__get_all_episodes(metadata)

        # 다운로드 가능한 에피소드 찾기
        downloadable_count, downloadable_episodes = self.__find_downloadable_episodes(
            all_episodes
        )

        # 데이터 정리해서 내보내기
        return WebtoonAnalysis(
            total_count=metadata.total_count,
            downloadable_count=downloadable_count,
            page_size=metadata.page_size,
            total_pages=metadata.total_pages,
            downloadable_episodes=downloadable_episodes,
            full_episodes=all_episodes,
        )


# 통합 테스트 함수
async def test_webtoon(title_id: int, webtoon_name: str):
    """웹툰 분석 테스트 함수"""
    print("\n" + "=" * 60)
    print(f"테스트: {webtoon_name} (titleId: {title_id})")
    print("=" * 60)

    analyzer = WebtoonAnalyzer(title_id)

    try:
        # 전체 분석 테스트
        print("전체 웹툰 분석 테스트...")
        result = await analyzer.analyze_webtoon()

        print(f"   전체 화수: {result.total_count}")
        print(f"   다운로드 가능한 화수: {result.downloadable_count}")
        print(f"   전체 에피소드 수: {len(result.full_episodes)}")
        print(f"   다운로드 가능한 에피소드 수: {len(result.downloadable_episodes)}")

        # 전체 에피소드 출력
        print("\n전체 에피소드 (처음 5개):")
        for episode in result.full_episodes[:5]:
            lock_status = "🔒" if episode.thumbnail_lock else "🔓"
            print(f"  {episode.no}화: {episode.subtitle} {lock_status}")

        print("\n전체 에피소드 (마지막 5개):")
        for episode in result.full_episodes[-5:]:
            lock_status = "🔒" if episode.thumbnail_lock else "🔓"
            print(f"  {episode.no}화: {episode.subtitle} {lock_status}")

        # 다운로드 가능한 에피소드 출력
        print("\n다운로드 가능한 에피소드 (처음 5개):")
        for episode in result.downloadable_episodes[:5]:
            lock_status = "🔒" if episode.thumbnail_lock else "🔓"
            print(f"  {episode.no}화: {episode.subtitle} {lock_status}")

        print("\n다운로드 가능한 에피소드 (마지막 5개):")
        for episode in result.downloadable_episodes[-5:]:
            lock_status = "🔒" if episode.thumbnail_lock else "🔓"
            print(f"  {episode.no}화: {episode.subtitle} {lock_status}")

        # 전체 에피소드에서 잠금 에피소드들 출력
        locked_episodes = [ep for ep in result.full_episodes if ep.thumbnail_lock]
        if locked_episodes:
            print(f"\n잠금 에피소드 목록 ({len(locked_episodes)}개):")
            for episode in locked_episodes:
                print(f"  {episode.no}화: {episode.subtitle}")

        # 요약 정보
        print("\n요약:")
        print(f"  전체 화수: {result.total_count}")
        print(f"  다운로드 가능: {result.downloadable_count}화")
        print(f"  잠금 상태: {len(locked_episodes)}화")
        print(
            f"  다운로드 가능 비율: {result.downloadable_count/len(result.full_episodes)*100:.1f}%"
        )

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


if __name__ == "__main__":
    asyncio.run(main())
