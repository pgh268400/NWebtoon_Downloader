# -*- coding: utf-8 -*-
from module.ImageMerger import *
from sys import exit
# 웹툰 다운로드 Class
from module.Nwebtoon import *
import os

# OS가 윈도우인 경우만 타이틀 변경 허용 (리눅스에선 아래 코드가 동작하지 않음)
if os.name == 'nt':
    import ctypes
    ctypes.windll.kernel32.SetConsoleTitleW("NWebtoon Downloader v4")

# 이미지 병합 Class
if __name__ == "__main__":
    dialog = input('모드를 선택해주세요 d : 다운로드 , m : 이미지합치기 : ')
    if dialog.lower() == 'd':
        query = input("정보를 입력해주세요(웹툰ID, URL, 웹툰제목) : ")
        if query.strip() != '':
            webtoon = NWebtoon(query)  # 객체 생성
            title_id = webtoon.title_id
        else:
            input("입력값이 없습니다..")
            exit()

        print('-------------------------------')
        print(f"웹툰명 : {webtoon.title}")
        print(f"총화수 : {webtoon.number}화")
        print(f"종류 : {webtoon.wtype}")
        print(webtoon.content)
        print('-------------------------------')

        if webtoon.isadult:
            print('성인 웹툰입니다. 로그인 정보를 입력해주세요.')
            NID_AUT = input("NID_AUT : ")
            NID_SES = input("NID_SES : ")
            webtoon.set_session(NID_AUT, NID_SES)  # 객체에 세션 데이터 넘기기

        dialog = input('몇화부터 몇화까지 다운로드 받으시겠습니까? 예) 1-10 , 5: ')
        dialog = dialog.strip()

        if dialog.find('-') == -1:  # 숫자만 입력했을때
            download_number = dialog
            webtoon.single_download(download_number)
        elif int(dialog.split('-')[1]) > webtoon.number:  # 최대화수 초과했을때
            input("최대화수를 초과했습니다")
        else:  # 일반 다운로드일때
            download_number_lst = dialog
            webtoon.multi_download(download_number_lst)
            input('다운로드가 완료되었습니다.')
    elif dialog.lower() == 'm':
        path = input("병합할 웹툰 경로를 입력해주세요 : ")
        image = ImageMerger(path)
        image.print_lists()
        image.merge()
        input('작업이 완료되었습니다.')
    else:
        input('올바르지 않은 입력입니다.')
