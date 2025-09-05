import asyncio
import aiohttp
import sys
import os
import time
from dataclasses import dataclass, field
from typing import List, Optional
from bs4 import BeautifulSoup

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from module.webtoon.analyzer import EpisodeInfo, WebtoonAnalyzer
from module.headers import headers


@dataclass
class EpisodeImageInfo(EpisodeInfo):
    """에피소드 정보 + 각 에피소드의 이미지 URL을 담는 데이터 클래스"""

    img_urls: List[str] = field(default_factory=list)


class WebtoonDownloader:
    """웹툰 다운로드 관련 기능을 담당하는 클래스"""

    def __init__(
        self,
        title_id: int,
        nid_aut: Optional[str] = None,
        nid_ses: Optional[str] = None,
    ) -> None:
        self.__title_id = title_id
        self.__detail_url = "https://comic.naver.com/webtoon/detail"

        # 성인 웹툰용 쿠키 설정
        self.__cookies = {}
        if nid_aut and nid_ses:
            self.__cookies = {"NID_AUT": nid_aut, "NID_SES": nid_ses}

    async def get_episode_images(
        self, episode: EpisodeImageInfo, verbose: bool = False
    ) -> EpisodeImageInfo:
        """
        특정 에피소드의 이미지 URL들을 가져오는 함수

        Args:
            episode: 에피소드 정보
            verbose: 상세 시간 정보 출력 여부 (기본값: False)

        Returns:
            이미지 URL이 추가된 에피소드 정보
        """
        url = f"{self.__detail_url}?titleId={self.__title_id}&no={episode.no}"

        try:
            async with aiohttp.ClientSession(
                headers=headers, cookies=self.__cookies
            ) as session:
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
                        if verbose:
                            print(
                                f"  {episode.no}화: {len(img_urls)}개 이미지 URL 수집 완료 (HTML: {html_time:.3f}s, 파싱: {parse_time:.3f}s, 총: {total_parse_time:.3f}s)"
                            )
                        else:
                            print(
                                f"  {episode.no}화: {len(img_urls)}개 이미지 URL 수집 완료"
                            )
                    else:
                        print(f"  {episode.no}화: HTTP 요청 실패 ({response.status})")
                        episode.img_urls = []
        except Exception as e:
            print(f"  {episode.no}화: 이미지 URL 수집 중 오류 발생 - {e}")
            episode.img_urls = []

        return episode

    async def get_episodes_with_images(
        self, episodes: List[EpisodeImageInfo], verbose: bool = False
    ) -> List[EpisodeImageInfo]:
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
        self, episodes: List[EpisodeImageInfo], batch_size: int
    ) -> List[EpisodeImageInfo]:
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

    async def download_episode_images(self, episode: EpisodeImageInfo) -> bool:
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
            print("    다운로드 준비 완료 (실제 다운로드 로직은 별도 구현 필요)")

            return True
        except Exception as e:
            print(f"  {episode.no}화: 다운로드 중 오류 발생 - {e}")
            return False

    async def download_episodes(self, episodes: List[EpisodeImageInfo]) -> List[bool]:
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
        self, episodes: List[EpisodeImageInfo], batch_size: int
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

        success_count = sum(download_results)
        print(f"\n총 {len(episodes)}개 에피소드 중 {success_count}개 다운로드 완료!")

        return download_results

    async def download(self, episodes: List[EpisodeInfo], batch_size) -> bool:
        """
        웹툰 다운로드 함수

        Args:
            episodes: 다운로드할 에피소드 리스트
            batch_size: 한 번에 처리할 배치 크기

        Returns:
            다운로드 성공 여부
        """
        if not episodes:
            print("다운로드할 에피소드가 없습니다.")
            return False

        print(f"\n{'='*60}")
        print(
            f"웹툰 다운로드 시작 - {len(episodes)}개 에피소드 (배치 크기: {batch_size})"
        )
        print(f"대상 에피소드: {episodes[0].no}화 ~ {episodes[-1].no}화")
        print(f"{'='*60}")

        try:
            # EpisodeInfo를 EpisodeImageInfo로 변환
            episode_image_infos = []
            for episode in episodes:
                episode_image_info = EpisodeImageInfo(
                    no=episode.no,
                    subtitle=episode.subtitle,
                    thumbnail_lock=episode.thumbnail_lock,
                )
                episode_image_infos.append(episode_image_info)

            # 배치 단위로 이미지 URL 수집
            print("\n이미지 URL 수집 시작...")
            episodes_with_images = await self.get_episodes_with_images_batch(
                episode_image_infos, batch_size
            )

            # 수집된 이미지 통계
            total_images = sum(
                len(episode.img_urls) for episode in episodes_with_images
            )
            print(f"총 수집된 이미지 수: {total_images}개")

            # 배치 단위로 다운로드 실행
            print("\n다운로드 시작...")
            download_results = await self.download_episodes_batch(
                episodes_with_images, batch_size
            )

            # 결과 요약
            success_count = sum(download_results)
            total_count = len(download_results)
            success_rate = (success_count / total_count * 100) if total_count > 0 else 0

            print(f"\n{'='*60}")
            print("다운로드 완료!")
            print(
                f"성공: {success_count}/{total_count}개 에피소드 ({success_rate:.1f}%)"
            )
            print(f"총 이미지 수: {total_images}개")
            print(f"{'='*60}")

            return success_count == total_count

        except Exception as e:
            print(f"다운로드 중 오류 발생: {e}")
            import traceback

            traceback.print_exc()
            return False

    @property
    def title_id(self) -> int:
        """타이틀 id"""
        return self.__title_id

    @property
    def nid_aut(self) -> Optional[str]:
        """NID_AUT 쿠키 값"""
        return self.__cookies.get("NID_AUT")

    @property
    def nid_ses(self) -> Optional[str]:
        """NID_SES 쿠키 값"""
        return self.__cookies.get("NID_SES")


# WebtoonDownloader 테스트 함수
async def test_downloader(title_id: int, start: int, end: int, batch_size: int):
    """WebtoonDownloader의 download() 함수를 테스트"""
    try:
        # WebtoonAnalyzer로 에피소드 정보 가져오기
        analyzer = await WebtoonAnalyzer.create(title_id)

        print(f"웹툰 제목: {analyzer.title_name}")
        print(f"성인 웹툰 여부: {analyzer.is_adult}")

        if analyzer.is_adult:
            print("성인 웹툰은 테스트를 지원하지 않습니다.")
            return

        # 지정된 범위의 에피소드 필터링
        all_episodes = analyzer.downloadable_episodes
        target_episodes = [ep for ep in all_episodes if start <= ep.no <= end]

        if not target_episodes:
            print(f"{start}화~{end}화 범위에 다운로드 가능한 에피소드가 없습니다.")
            return

        # 다운로더로 다운로드 실행
        downloader = WebtoonDownloader(title_id)
        success = await downloader.download(target_episodes, batch_size)
        print(f"테스트 결과: {'성공' if success else '실패'}")

    except Exception as e:
        print(f"테스트 중 오류 발생: {e}")


async def test_multiple_downloaders():
    """WebtoonDownloader 테스트 - 지정된 title ID들로 테스트"""
    print("WebtoonDownloader 테스트 시작")

    # 테스트할 title ID들과 화수 범위
    test_cases = [
        # (835801, 1, 2, 5),  # 달마건
        (183559, 1, 653, 5),  # 신의 탑
        # (602287, 1, 2, 5),  # 뷰티풀 군바리
    ]

    for title_id, start, end, batch_size in test_cases:
        print(f"\n=== 타이틀 ID: {title_id} ({start}화~{end}화) ===")
        await test_downloader(title_id, start, end, batch_size)


# 메인 실행부
if __name__ == "__main__":
    asyncio.run(test_multiple_downloaders())
