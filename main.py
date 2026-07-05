import asyncio
from typing import Optional
from module.image_merger import ImageMerger
from module.webtoon.analyzer import WebtoonAnalyzer
from module.webtoon.downloader import WebtoonDownloader
from module.webtoon.search import WebtoonSearch
from module.input_validate import (
    input_until_correct_download_range,
    input_until_get_data,
)
from module.settings import Setting
from module.html_maker import HtmlMaker
from sys import exit
from rich import print
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import os
from module.title_changer import change_title


async def main() -> None:
    # 윈도우에서 실행한 경우 콘솔 타이틀 변경
    change_title()

    # 세팅 파일 없으면 자동 생성 & 값 읽기
    s = Setting()
    while True:
        try:
            print("::[bold green]NWebtoon Downloader[/bold green]::")
            print("<모드를 선택해주세요>")
            print("[magenta]d[/magenta] : 다운로드")
            print("[magenta]o[/magenta] : 다운로드 폴더 열기")
            print("[magenta]m[/magenta] : 이미지 병합")
            print("[red]q[/red] : 프로그램 종료")
            # print('[magenta]h[/magenta] : HTML 생성')
            dialog = input(">>> ")
            if dialog.lower() == "d":
                # 공백이 아닐때까지 입력을 받는다
                query = input_until_get_data(
                    default_prompt=">>> 정보를 입력해주세요 (웹툰ID, URL, 웹툰제목) : "
                )

                # 객체 생성 -> 유저한테 입력받은 정보를 토대로 title_id 얻기
                title_id: int = WebtoonSearch(query).title_id

                # title_id를 이용해 웹툰 정보 파싱
                analyzer = await WebtoonAnalyzer.create(title_id)

                # 성인 웹툰 인증용 쿠키
                nid_aut: Optional[str] = None
                nid_ses: Optional[str] = None

                if analyzer.is_adult:
                    print("성인 웹툰입니다. 로그인 정보가 필요합니다.")
                    print("NID_AUT와 NID_SES 쿠키 값을 입력해주세요.")

                    nid_aut = input("NID_AUT : ").strip()
                    nid_ses = input("NID_SES : ").strip()

                    if not nid_aut or not nid_ses:
                        raise Exception("NID_AUT와 NID_SES 값이 필요합니다.")
                    else:
                        # nid_aut, nid_ses 입력시 analyzer 객체 갱신 (재생성)
                        analyzer = await WebtoonAnalyzer.create(
                            title_id, nid_aut, nid_ses
                        )

                        print(analyzer.__dict__)

                # 분석된 웹툰 정보를 Rich 패널로 표시 (downloader.py 디자인 참고)
                console = Console()

                info_table = Table(show_header=False, box=None, padding=(0, 1))
                info_table.add_column("라벨", style="cyan bold", width=30)
                info_table.add_column("값", style="white")

                info_table.add_row("웹툰명:", analyzer.title_name)
                info_table.add_row(
                    "총 에피소드 수:", f"{len(analyzer.full_episodes)}화"
                )
                info_table.add_row(
                    "다운로드 가능한 에피소드 수:",
                    f"{len(analyzer.downloadable_episodes)}화",
                )
                info_table.add_row("종류:", str(analyzer.webtoon_type))
                info_table.add_row("소개:", analyzer.synopsis)

                info_panel = Panel(
                    info_table,
                    title="[bold green]📚 웹툰 정보[/bold green]",
                    border_style="green",
                    padding=(1, 2),
                )
                console.print(info_panel)

                # 입력값 검증 : "숫자" 또는 "숫자-숫자" 만 입력할때까지 입력을 받는다.
                dialog = input_until_correct_download_range(
                    default_prompt="몇화부터 몇화까지 다운로드 받으시겠습니까? 예) 1-10 , 5: ",
                    error_prompt=">>> 다시 입력해주세요. 예) 1-10 , 5: ",
                )

                # 다운로드 객체 생성
                downloader = WebtoonDownloader(
                    analyzer.title_id,
                    analyzer.downloadable_episodes,
                    analyzer.title_name,
                    analyzer.webtoon_type,
                    nid_aut,
                    nid_ses,
                )

                # 검증된 입력값에 대해 다운로드 진행
                if (
                    dialog.find("-") == -1
                ):  # 숫자만 입력했을때 ("-" 입력하지 않고 순수한 문자만 입력시)
                    start = int(dialog)
                    await downloader.download(start=start, end=start)
                    input("다운로드가 완료되었습니다.")
                else:  # 일반 다운로드일때
                    download_number_lst = list(
                        map(int, dialog.split("-"))
                    )  # "1-2" -> [1,2]
                    start, end = download_number_lst
                    await downloader.download(start=start, end=end)
                    input("다운로드가 완료되었습니다.")
            elif dialog.lower() == "m":
                path = input("병합할 웹툰 경로를 입력해주세요 : ")
                image = ImageMerger(path)
                image.print_lists()
                image.run()
                input("작업이 완료되었습니다.")
            elif dialog.lower() == "h":
                # 아직 해당 기능은 미구현 상태
                print(
                    "히든 기능 발견! 해당 기능은 아직 개발중입니다. 버그 발생해도 책임지지 않습니다."
                )
                path = input("HTML을 생성할 웹툰 경로를 입력해주세요 : ")
                html = HtmlMaker(path)
                html.print_lists()
                html.run()
                input("작업이 완료되었습니다.")
            elif dialog.lower() == "q":
                exit()
            elif dialog.lower() == "o":
                path = os.path.realpath(s.download_path)
                os.startfile(path)
                print("다운로드 폴더을 열었습니다.")
            else:
                input("올바르지 않은 입력입니다.")
                # 콘솔 청소 (Cross-Platform)
                os.system("cls" if os.name == "nt" else "clear")
        except (KeyboardInterrupt, EOFError, asyncio.CancelledError):
            # Ctrl + C 강제 종료 처리
            print("\n사용자 입력으로 프로그램을 종료합니다.")
            exit(1)
        except Exception as e:
            print(e, type(e))
            input("오류가 발생했습니다.")


if __name__ == "__main__":
    asyncio.run(main())
