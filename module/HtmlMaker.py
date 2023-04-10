import os
import re
from pathlib import Path
import chardet
from .ImageMerger import ImageMerger
from jinja2 import Template  # html 템플릿용
import natsort

# 파이썬 3에서는 모든 import 문은 기본적으로 절대(absolute) import다.
# 만약 파이썬 3에서 상대 import를 사용하고 싶다면 위처럼 (.) 으로 명시적으로 표현을 해주어야 한다.
# 또한 패키지 경로의 기준은 __name__ == "__main__" 을 실행시키는 위치가 된다.
# 그러므로 해당 코드 테스트를 원하면 이 코드를 직접 실행할 것이 아닌, main.py를 실행해야 한다.
# 파이썬의 모든 import 구문은 절대 경로이다.

# ImageMerger 을 상속받아 구현


class HtmlMaker(ImageMerger):
    def __init__(self, path) -> None:
        super().__init__(path)  # 부모 생성자 호출
        self.__title = os.path.basename(path)  # 웹툰 제목
        self.__user_input_path = path  # 사용자가 입력한 경로

    def __read_file(self, path) -> str:
        # 파일 열어서 인코딩 확인
        rawdata = open(path, 'rb').read()
        result = chardet.detect(rawdata)
        enc = result['encoding']

        # 인코딩 맞게 열기
        f = open(path, "r", encoding=enc)
        line = f.readline()

        data = ""
        while line:
            data += line
            line = f.readline()
        f.close()
        return data

    # ImagerMerger 오버라이딩으로 구현
    # 실제 run() 이 호출해서 처리해주는 함수
    # Python __ : private, _ : protected
    def _processing(self, file_lst: list) -> None:
        try:
            # 파일리스트가 비었으면 처리하지 않는다
            if not file_lst:
                return

            rel_base_path: str = os.path.dirname(
                file_lst[0])  # 웹툰이 저장되어 있는 폴더 경로
            base_path: str = os.path.abspath(rel_base_path)  # 절대경로로 변환
            print("기반 경로 : ", base_path)

            # 폴더명에서 숫자만 추출 (몇화를 작업하고 있는지 숫자 저장)
            numbers = int(re.findall(r'\[(\d+)\]', base_path)[0])

            # 기존에 생성한 index.html을 삭제한다.
            output_path = os.path.join(base_path, 'index.html')

            if os.path.isfile(output_path):
                os.remove(output_path)

            # html template 을 위한 데이터를 생성한다.
            episode = os.path.basename(os.path.dirname(file_lst[0]))
            episode = " ".join(episode.split()[1:])

            img_lst = []
            for file in file_lst:
                # file 소문자로 변환
                file = file.lower()

                # 이미지 파일이고, output.png가 아닌 경우만 추가한다.
                if file.endswith('output.png'):
                    continue

                if file.endswith('.png') or file.endswith('.jpg') or file.endswith('.jpeg'):
                    img_lst.append(os.path.basename(file))

            # print(img_lst)

            # 부모 경로에서 [다음화] 로 시작하는 폴더 이름을 가져온다.
            parent_path = os.path.dirname(base_path)
            next_folder_name = next((folder for folder in os.listdir(
                parent_path) if folder.startswith(f'[{numbers+1}]')), None)

            print(parent_path)

            if next_folder_name:
                next_web = os.path.join("../", next_folder_name, "index.html")
            else:
                # print("[다음화]로 시작하는 폴더를 찾지 못했습니다.")
                next_web = "javascript:alert('마지막화 입니다.');"

            # 부모 경로에서 [이전화] 로 시작하는 폴더 이름을 가져온다.
            parent_path = os.path.dirname(base_path)
            prev_folder_name = next((folder for folder in os.listdir(
                parent_path) if folder.startswith(f'[{numbers-1}]')), None)

            if prev_folder_name:
                prev_web = os.path.join("../", prev_folder_name, "index.html")
            else:
                # print("[이전화]로 시작하는 폴더를 찾지 못했습니다.")
                prev_web = "javascript:alert('처음화 입니다.');"

            # template.html을 읽고, 데이터를 채운다.
            html_data = self.__read_file("./module/template.html")
            html_data = Template(html_data).render(
                title=self.__title, episode=episode, img_lst=img_lst, prev=prev_web, next=next_web)

            # index.html 파일을 생성한다.
            index_path = os.path.join(base_path, 'index.html')
            f = open(index_path, 'w', encoding="UTF-8")
            f.write(html_data)
            f.close()
            print(f"{index_path} 생성 완료")

        except Exception as e:
            raise e

    def __make_index(self, user_input_path):
        print(f"{user_input_path} 위치에 색인을 생성중입니다...")

        # 현재 경로를 기준으로 모든 폴더를 리스트로 가져온다
        dir_lst = os.listdir(user_input_path)
        dir_lst = natsort.natsorted(dir_lst)  # natural sort 로 정렬

        pure_name_lst = []

        # 이름 리스트에서 앞의 순번은 제거
        for element in dir_lst:
            item = os.path.basename(element)
            item = " ".join(item.split()[1:])
            pure_name_lst.append(item)

        html_path = [
            os.path.join(self.__title, element, "index.html") for element in dir_lst]

        item_lst = list(zip(html_path, pure_name_lst))

        # template을 읽고, 데이터를 채운다.
        html_data = self.__read_file("./module/template2.html")
        html_data = Template(html_data).render(
            title=self.__title, item_lst=item_lst)

        # index.html 파일을 생성한다.
        # index_path = os.path.join(user_input_path, 'index.html')
        f = open(f'{self.__title}.html', 'w', encoding="UTF-8")
        f.write(html_data)
        f.close()
        print(f"전체 인덱스 파일 생성 완료")

    # ImageMerger 와 동일한 인터페이스 제공

    def run(self):
        self.__make_index(self.__user_input_path)  # html 전체 색인 생성 함수
        super().run()  # 부모 클래스의 run() 호출, 실제로 각 폴더에 html Processing 해주는 함수
