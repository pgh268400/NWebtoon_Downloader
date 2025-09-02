import asyncio
import aiohttp
import sys
import os
from typing import Dict, List, Tuple
from dataclasses import dataclass

# 상위 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 기존 pydantic 타입 정의 import
from type.api.article_list import NWebtoonArticleListData, ArticleItem


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
    episodes: List[EpisodeInfo]


class WebtoonAnalyzer:
    """웹툰 분석기 클래스"""

    def __init__(self):
        self.base_url = "https://comic.naver.com/api/article/list"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    async def get_total_episode_count(self, title_id: int) -> int:
        """
        웹툰의 전체 화수를 가져오는 함수

        Args:
            title_id: 웹툰의 titleId

        Returns:
            전체 화수
        """
        url = f"{self.base_url}?titleId={title_id}&page=1"

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    # pydantic 모델을 사용하여 데이터 검증
                    article_list_data = NWebtoonArticleListData.from_dict(data)
                    return article_list_data.totalCount
                else:
                    raise Exception(f"API 요청 실패: {response.status}")

    async def get_episode_list_page(
        self, title_id: int, page: int
    ) -> NWebtoonArticleListData:
        """
        특정 페이지의 에피소드 리스트를 가져오는 함수

        Args:
            title_id: 웹툰의 titleId
            page: 페이지 번호

        Returns:
            해당 페이지의 pydantic 모델 데이터
        """
        url = f"{self.base_url}?titleId={title_id}&page={page}"

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    # pydantic 모델을 사용하여 데이터 검증 및 변환
                    return NWebtoonArticleListData.from_dict(data)
                else:
                    raise Exception(f"페이지 {page} 요청 실패: {response.status}")

    def calculate_total_pages(self, total_count: int, page_size: int = 20) -> int:
        """
        전체 페이지 수를 계산하는 함수

        Args:
            total_count: 전체 화수
            page_size: 페이지당 화수 (기본값: 20)

        Returns:
            전체 페이지 수
        """
        return (total_count + page_size - 1) // page_size

    async def get_all_episodes(self, title_id: int) -> List[EpisodeInfo]:
        """
        모든 에피소드 정보를 가져오는 함수

        Args:
            title_id: 웹툰의 titleId

        Returns:
            모든 에피소드 정보 리스트
        """
        # 먼저 전체 화수를 가져옴
        total_count = await self.get_total_episode_count(title_id)

        # 전체 페이지 수 계산
        total_pages = self.calculate_total_pages(total_count)

        # 모든 페이지를 병렬로 요청
        tasks = []
        for page in range(1, total_pages + 1):
            task = self.get_episode_list_page(title_id, page)
            tasks.append(task)

        # 모든 요청을 동시에 실행
        responses = await asyncio.gather(*tasks)

        # 모든 에피소드 정보를 수집
        all_episodes = []

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

    def find_downloadable_episodes(
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

    async def analyze_webtoon(self, title_id: int) -> WebtoonAnalysis:
        """
        웹툰을 분석하는 메인 함수

        Args:
            title_id: 웹툰의 titleId

        Returns:
            웹툰 분석 결과
        """
        # 전체 화수 가져오기
        total_count = await self.get_total_episode_count(title_id)

        # 모든 에피소드 정보 가져오기
        all_episodes = await self.get_all_episodes(title_id)

        # 다운로드 가능한 에피소드 찾기
        downloadable_count, downloadable_episodes = self.find_downloadable_episodes(
            all_episodes
        )

        return WebtoonAnalysis(
            total_count=total_count,
            downloadable_count=downloadable_count,
            episodes=all_episodes,
        )


# 테스트 케이스들
async def test_case_1():
    """테스트 케이스 1: 마음의소리2 (titleId: 717481)"""
    print("\n" + "=" * 60)
    print("테스트 케이스 1: 마음의소리2 (titleId: 717481)")
    print("=" * 60)

    analyzer = WebtoonAnalyzer()
    title_id = 717481

    try:
        result = await analyzer.analyze_webtoon(title_id)

        print(f"전체 화수: {result.total_count}")
        print(f"다운로드 가능한 화수: {result.downloadable_count}")
        print(f"전체 에피소드 수: {len(result.episodes)}")

        # 처음 5개와 마지막 5개 에피소드 출력
        print("\n처음 5개 에피소드:")
        for episode in result.episodes[:5]:
            lock_status = "🔒" if episode.thumbnail_lock else "🔓"
            print(f"  {episode.no}화: {episode.subtitle} {lock_status}")

        print("\n마지막 5개 에피소드:")
        for episode in result.episodes[-5:]:
            lock_status = "🔒" if episode.thumbnail_lock else "🔓"
            print(f"  {episode.no}화: {episode.subtitle} {lock_status}")

        # 잠금 에피소드들 출력
        locked_episodes = [ep for ep in result.episodes if ep.thumbnail_lock]
        if locked_episodes:
            print(f"\n잠금 에피소드 목록 ({len(locked_episodes)}개):")
            for episode in locked_episodes:
                print(f"  {episode.no}화: {episode.subtitle}")

        # 요약 정보
        print(f"\n요약:")
        print(f"  전체 화수: {result.total_count}")
        print(f"  다운로드 가능: {result.downloadable_count}화")
        print(f"  잠금 상태: {len(locked_episodes)}화")
        print(
            f"  다운로드 가능 비율: {result.downloadable_count/len(result.episodes)*100:.1f}%"
        )

    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback

        traceback.print_exc()


async def test_case_2():
    """테스트 케이스 2: 뷰티풀 군바리 (titleId: 842399)"""
    print("\n" + "=" * 60)
    print("테스트 케이스 2: 뷰티풀 군바리 (titleId: 842399)")
    print("=" * 60)

    analyzer = WebtoonAnalyzer()
    title_id = 842399

    try:
        result = await analyzer.analyze_webtoon(title_id)

        print(f"전체 화수: {result.total_count}")
        print(f"다운로드 가능한 화수: {result.downloadable_count}")
        print(f"전체 에피소드 수: {len(result.episodes)}")

        # 처음 5개와 마지막 5개 에피소드 출력
        print("\n처음 5개 에피소드:")
        for episode in result.episodes[:5]:
            lock_status = "🔒" if episode.thumbnail_lock else "🔓"
            print(f"  {episode.no}화: {episode.subtitle} {lock_status}")

        print("\n마지막 5개 에피소드:")
        for episode in result.episodes[-5:]:
            lock_status = "🔒" if episode.thumbnail_lock else "🔓"
            print(f"  {episode.no}화: {episode.subtitle} {lock_status}")

        # 잠금 에피소드들 출력
        locked_episodes = [ep for ep in result.episodes if ep.thumbnail_lock]
        if locked_episodes:
            print(f"\n잠금 에피소드 목록 ({len(locked_episodes)}개):")
            for episode in locked_episodes:
                print(f"  {episode.no}화: {episode.subtitle}")

        # 요약 정보
        print(f"\n요약:")
        print(f"  전체 화수: {result.total_count}")
        print(f"  다운로드 가능: {result.downloadable_count}화")
        print(f"  잠금 상태: {len(locked_episodes)}화")
        print(
            f"  다운로드 가능 비율: {result.downloadable_count/len(result.episodes)*100:.1f}%"
        )

    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback

        traceback.print_exc()


async def test_case_3():
    """테스트 케이스 3: 신의 탑 (titleId: 183559)"""
    print("\n" + "=" * 60)
    print("테스트 케이스 3: 신의 탑 (titleId: 183559)")
    print("=" * 60)

    analyzer = WebtoonAnalyzer()
    title_id = 183559

    try:
        result = await analyzer.analyze_webtoon(title_id)

        print(f"전체 화수: {result.total_count}")
        print(f"다운로드 가능한 화수: {result.downloadable_count}")
        print(f"전체 에피소드 수: {len(result.episodes)}")

        # 처음 5개와 마지막 5개 에피소드 출력
        print("\n처음 5개 에피소드:")
        for episode in result.episodes[:5]:
            lock_status = "🔒" if episode.thumbnail_lock else "🔓"
            print(f"  {episode.no}화: {episode.subtitle} {lock_status}")

        print("\n마지막 5개 에피소드:")
        for episode in result.episodes[-5:]:
            lock_status = "🔒" if episode.thumbnail_lock else "🔓"
            print(f"  {episode.no}화: {episode.subtitle} {lock_status}")

        # 잠금 에피소드들 출력
        locked_episodes = [ep for ep in result.episodes if ep.thumbnail_lock]
        if locked_episodes:
            print(f"\n잠금 에피소드 목록 ({len(locked_episodes)}개):")
            for episode in locked_episodes:
                print(f"  {episode.no}화: {episode.subtitle}")

        # 요약 정보
        print(f"\n요약:")
        print(f"  전체 화수: {result.total_count}")
        print(f"  다운로드 가능: {result.downloadable_count}화")
        print(f"  잠금 상태: {len(locked_episodes)}화")
        print(
            f"  다운로드 가능 비율: {result.downloadable_count/len(result.episodes)*100:.1f}%"
        )

    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback

        traceback.print_exc()


# 메인 테스트 함수
async def main():
    """웹툰 분석기 테스트 - 여러 웹툰으로 테스트"""
    print("웹툰 분석기 테스트 시작")
    print("pydantic 타입 정의를 활용한 버전")

    # 여러 테스트 케이스 실행
    await test_case_1()  # 마음의소리2
    await test_case_2()  # 뷰티풀 군바리
    await test_case_3()  # 신의 탑

    print("\n" + "=" * 60)
    print("모든 테스트 완료!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
