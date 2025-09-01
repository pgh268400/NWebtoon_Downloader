from module.image_merger import ImageMerger
from module.nwebtoon import NWebtoon
from module.input_validate import (
    input_until_correct_download_range,
    input_until_get_data,
)
from module.settings import Setting
from module.html_maker import HtmlMaker
from sys import exit
from rich import print
import os

# 콘솔창 타이틀 변경 (윈도우 전용)
WINDOW_TITLE = "NWebtoon Downloader v5.3-NEW"

# OS가 윈도우인 경우만 타이틀 변경 허용 (리눅스에선 아래 코드가 동작하지 않음)
if os.name == "nt":
    import ctypes

    ctypes.windll.kernel32.SetConsoleTitleW(WINDOW_TITLE)

if __name__ == "__main__":
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
                    default_prompt=">>> 정보를 입력해주세요(웹툰ID, URL, 웹툰제목) : "
                )
                webtoon = NWebtoon(query)  # 객체 생성 -> 웹툰 데이터 파싱

                print("-------------------------------")
                print(f"[bold green]웹툰명[/bold green] : {webtoon.title}")
                print(f"[bold green]총화수[/bold green] : {webtoon.number}화")
                print(f"[bold green]종류[/bold green] : {webtoon.wtype}")
                print(webtoon.content)
                print("-------------------------------")

                # 입력값 검증 : "숫자" 또는 "숫자-숫자" 만 입력할때까지 입력을 받는다.

                dialog = input_until_correct_download_range(
                    default_prompt="몇화부터 몇화까지 다운로드 받으시겠습니까? 예) 1-10 , 5: ",
                    error_prompt=">>> 다시 입력해주세요. 예) 1-10 , 5: ",
                )

                # 검증된 입력값에 대해 다운로드 진행
                if (
                    dialog.find("-") == -1
                ):  # 숫자만 입력했을때 ("-" 입력하지 않고 순수한 문자만 입력시)
                    download_number = int(dialog)
                    webtoon.multi_download(download_number, download_number)
                    input("다운로드가 완료되었습니다.")
                elif int(dialog.split("-")[1]) > webtoon.number:  # 최대화수 초과했을때
                    input("최대화수를 초과했습니다")
                elif int(dialog.split("-")[1]) <= 0:
                    input("0또는 음수는 입력하실 수 없습니다.")
                else:  # 일반 다운로드일때
                    download_number_lst = list(
                        map(int, dialog.split("-"))
                    )  # "1-2" -> [1,2]
                    start, end = download_number_lst
                    webtoon.multi_download(start, end)
                    input("다운로드가 완료되었습니다.")
            elif dialog.lower() == "m":
                path = input("병합할 웹툰 경로를 입력해주세요 : ")
                image = ImageMerger(path)
                image.print_lists()
                image.run()
                input("작업이 완료되었습니다.")
            elif dialog.lower() == "h":
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
        except Exception as e:
            print(e)
            input("오류가 발생했습니다.")
