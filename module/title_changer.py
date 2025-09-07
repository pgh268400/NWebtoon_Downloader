import os
import ctypes

# 콘솔창 타이틀 변경 (윈도우 전용)
WINDOW_TITLE = "NWebtoon Downloader v5.3-NEW"


def change_title() -> None:
    # OS가 윈도우인 경우만 타이틀 변경 허용 (리눅스에선 아래 코드가 동작하지 않음)
    if os.name == "nt":
        ctypes.windll.kernel32.SetConsoleTitleW(WINDOW_TITLE)
