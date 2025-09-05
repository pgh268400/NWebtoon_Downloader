import asyncio
import aiohttp
import sys
import os
import time
from dataclasses import dataclass
from typing import List, Optional
from bs4 import BeautifulSoup

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from module.webtoon.analyzer import EpisodeInfo
from module.headers import headers


@dataclass
class EpisodeImageInfo(EpisodeInfo):
    """에피소드 정보 + 각 에피소드의 이미지 URL을 담는 데이터 클래스"""

    img_urls: List[str] = []


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
            print("    다운로드 준비 완료 (실제 다운로드 로직은 별도 구현 필요)")

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

