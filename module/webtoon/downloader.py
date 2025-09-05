import asyncio
import aiohttp
import aiofiles
import sys
import os
import time
from dataclasses import dataclass, field
from typing import List, Optional
from bs4 import BeautifulSoup
from pathlib import Path

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

    # 생성자 처리
    def __init__(
        self,
        title_id: int,
        episodes: List[EpisodeInfo],
        nid_aut: Optional[str] = None,
        nid_ses: Optional[str] = None,
    ) -> None:
        self.__title_id = title_id
        self.__episodes = episodes
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

    async def __download_single_image(
        self, session: aiohttp.ClientSession, img_url: str, file_path: Path
    ) -> bool:
        """
        단일 이미지를 다운로드하는 함수

        Args:
            session: aiohttp 세션
            img_url: 이미지 URL
            file_path: 저장할 파일 경로

        Returns:
            다운로드 성공 여부
        """
        try:
            async with session.get(img_url, headers=headers) as response:
                if response.status == 200:
                    # 디렉토리가 없으면 생성
                    file_path.parent.mkdir(parents=True, exist_ok=True)

                    async with aiofiles.open(file_path, "wb") as f:
                        async for chunk in response.content.iter_chunked(8192):
                            await f.write(chunk)
                    return True
                else:
                    print(
                        f"    이미지 다운로드 실패: {img_url} (HTTP {response.status})"
                    )
                    return False
        except Exception as e:
            print(f"    이미지 다운로드 오류: {img_url} - {e}")
            return False

    async def __download_all_images_concurrent(
        self, episodes: List[EpisodeImageInfo], max_concurrent: int = 10
    ) -> List[bool]:
        """
        모든 에피소드의 이미지를 동시성 제한을 걸어 한꺼번에 다운로드하는 함수

        Args:
            episodes: 이미지 URL이 포함된 에피소드 리스트
            max_concurrent: 최대 동시 다운로드 수 (기본값: 10)

        Returns:
            각 에피소드의 다운로드 성공 여부 리스트
        """
        if not episodes:
            print("다운로드할 에피소드가 없습니다.")
            return []

        # 전체 이미지 수 계산
        total_images = sum(len(episode.img_urls) for episode in episodes)
        print(f"총 {len(episodes)}개 에피소드, {total_images}개 이미지를 동시 다운로드합니다...")
        print(f"최대 동시 다운로드: {max_concurrent}개")

        # 세마포어로 전체 이미지 다운로드 동시성 제한
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def download_single_episode_image(session, episode, img_url, img_idx):
            """단일 에피소드의 단일 이미지 다운로드"""
            async with semaphore:
                # 다운로드 폴더 생성
                download_dir = Path("Webtoon_Download") / f"[{episode.no}] {episode.subtitle}"
                
                # 파일 확장자 추출 (기본값: .jpg)
                ext = ".jpg"
                if "." in img_url.split("/")[-1]:
                    ext = "." + img_url.split(".")[-1].split("?")[0]
                
                file_path = download_dir / f"{img_idx+1:03d}{ext}"
                return await self.__download_single_image(session, img_url, file_path)

        try:
            async with aiohttp.ClientSession(cookies=self.__cookies) as session:
                # 모든 에피소드의 모든 이미지를 하나의 태스크 리스트로 생성
                all_tasks = []
                episode_task_counts = []  # 각 에피소드별 태스크 수 기록
                
                for episode in episodes:
                    if not hasattr(episode, "img_urls") or not episode.img_urls:
                        print(f"  {episode.no}화: 다운로드할 이미지 URL이 없습니다.")
                        episode_task_counts.append(0)
                        continue
                    
                    episode_task_counts.append(len(episode.img_urls))
                    
                    # 해당 에피소드의 모든 이미지 태스크 생성
                    for img_idx, img_url in enumerate(episode.img_urls):
                        task = download_single_episode_image(session, episode, img_url, img_idx)
                        all_tasks.append(task)
                
                # 모든 이미지를 동시에 다운로드 (세마포어로 동시성 제한)
                print(f"\n전체 {len(all_tasks)}개 이미지 다운로드 시작...")
                all_results = await asyncio.gather(*all_tasks, return_exceptions=True)
                
                # 에피소드별 결과 집계
                episode_results = []
                result_idx = 0
                
                for i, episode in enumerate(episodes):
                    task_count = episode_task_counts[i]
                    if task_count == 0:
                        episode_results.append(False)
                        continue
                    
                    # 해당 에피소드의 결과들 추출
                    episode_task_results = all_results[result_idx:result_idx + task_count]
                    result_idx += task_count
                    
                    # 성공 개수 계산
                    success_count = sum(1 for result in episode_task_results if result is True)
                    episode_success = success_count == task_count
                    episode_results.append(episode_success)
                    
                    print(f"  {episode.no}화: {success_count}/{task_count}개 성공")
                
                return episode_results

        except Exception as e:
            print(f"이미지 다운로드 중 오류 발생: {e}")
            return [False] * len(episodes)

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

    async def __download_episodes_batch(
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

    async def download(self, start: int, end: int, batch_size: int) -> bool:
        """
        웹툰 다운로드 함수

        Args:
            start: 시작 화수 (1부터 시작)
            end: 끝 화수 (1부터 시작)
            batch_size: 한 번에 처리할 배치 크기

        Returns:
            다운로드 성공 여부
        """
        if not self.__episodes:
            print("다운로드할 에피소드가 없습니다.")
            return False

        # 1-based index를 0-based index로 변환
        start_idx = start - 1
        end_idx = end - 1

        # 인덱스 범위 검증
        if start_idx < 0 or end_idx >= len(self.__episodes) or start_idx > end_idx:
            print(f"잘못된 화수 범위입니다. (1 ~ {len(self.__episodes)} 범위에서 선택)")
            return False

        # 선택된 에피소드 추출
        selected_episodes = self.__episodes[start_idx : end_idx + 1]

        print(f"\n{'='*60}")
        print(
            f"웹툰 다운로드 시작 - {len(selected_episodes)}개 에피소드 (배치 크기: {batch_size})"
        )
        print(f"인덱스 범위: {start} ~ {end}")
        print(
            f"대상 에피소드: {selected_episodes[0].no}화 ~ {selected_episodes[-1].no}화"
        )
        print(f"{'='*60}")

        try:
            # EpisodeInfo를 EpisodeImageInfo로 변환
            episode_image_infos = []
            for episode in selected_episodes:
                episode_image_info = EpisodeImageInfo(
                    no=episode.no,
                    subtitle=episode.subtitle,
                    thumbnail_lock=episode.thumbnail_lock,
                )
                episode_image_infos.append(episode_image_info)

            # 배치 단위로 이미지 URL 수집
            print("이미지 URL 수집 시작")
            episodes_with_images = await self.get_episodes_with_images_batch(
                episode_image_infos, batch_size
            )

            # 수집된 이미지 통계
            total_images = sum(
                len(episode.img_urls) for episode in episodes_with_images
            )
            print(f"총 수집된 이미지 수: {total_images}개")

            # 모든 에피소드의 이미지를 한꺼번에 다운로드 (동시성 제한 적용)
            print("\n다운로드 시작...")
            download_results = await self.__download_all_images_concurrent(
                episodes_with_images, max_concurrent=10
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
    def episodes(self) -> List[EpisodeInfo]:
        """다운로드 할 에피소드 리스트"""
        return self.__episodes

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

        # 다운로드 가능한 에피소드만 다운로드 (유료 회차 지원 X)
        downloadable_episodes = analyzer.downloadable_episodes

        # 다운로더로 다운로드 실행 (전체 에피소드 리스트와 함께 생성)
        downloader = WebtoonDownloader(title_id, downloadable_episodes)

        success = await downloader.download(start, end, batch_size)
        print(f"테스트 결과: {'성공' if success else '실패'}")

    except Exception as e:
        print(f"테스트 중 오류 발생: {e}")


async def test_case():
    """WebtoonDownloader 테스트 - 지정된 title ID들로 테스트"""
    print("WebtoonDownloader 테스트 시작")

    # 테스트할 title id들과 화수 범위
    test_cases = [
        # (835801, 1, 2, 5),  # 달마건
        (183559, 1, 5, 5),  # 신의 탑
        # (602287, 1, 2, 5),  # 뷰티풀 군바리
    ]

    for title_id, start, end, batch_size in test_cases:
        print(f"\n=== 타이틀 ID: {title_id} ({start}화~{end}화) ===")
        await test_downloader(title_id, start, end, batch_size)


# 메인 실행부
if __name__ == "__main__":
    asyncio.run(test_case())
