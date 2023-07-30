import os
import natsort
import cv2
import numpy as np


class ImageMerger:
    # 파이썬에서 private = 앞에 언더바 두개 (__)

    def __init__(self, dir_path) -> None:
        try:
            self.__dir_path = dir_path

            # 디렉토리를 순회하면서 리스트에 저장 (앞의 경로까지 다 저장)
            file_lst = os.listdir(self.__dir_path)

            for i in range(0, len(file_lst)):
                file_lst[i] = os.path.join(dir_path, file_lst[i])

            # 파일 리스트 기억
            self.__file_lst = file_lst  # 파일 리스트 기억
            self.__file_lst = natsort.natsorted(
                self.__file_lst)  # natural sort 로 정렬

            if not file_lst:  # 파일이 아무것도 없음.
                raise Exception('There is No File')  # 예외를 던짐
            else:  # 파일이 하나라도 존재하면
                file_count, dir_count = 0, 0
                for name in file_lst:
                    if os.path.isfile(name):
                        file_count += 1
                    if os.path.isdir(name):
                        dir_count += 1

                # 파일과 디렉토리가 동시에 존재할 경우
                if file_count > 0 and dir_count > 0:
                    raise Exception('Invalid file structure')  # 예외를 던짐
                # 디렉토리 안에 파일만 존재할경우
                elif file_count > 0 and dir_count == 0:
                    self.__pure_file = True
                # 디렉토리 안에 디렉토리만 존재할 경우
                else:
                    self.__pure_file = False
        except Exception as e:
            print(e)
            input()
            exit()

    # Private Method -------------------------------------------------------

    # 수직으로 합칠때, 큰 이미지가 있으면 작게 resize 후 붙이는 함수
    # https://note.nkmk.me/en/python-opencv-hconcat-vconcat-np-tile/
    def __vconcat_resize_min(self, im_list, interpolation=cv2.INTER_CUBIC):
        w_min = min(im.shape[1] for im in im_list)
        im_list_resize = [cv2.resize(im, (w_min, int(im.shape[0] * w_min / im.shape[1])), interpolation=interpolation)
                          for im in im_list]
        return cv2.vconcat(im_list_resize)

    # 코드 참고 : https://stackoverflow.com/questions/53876007/how-to-vertically-merge-two-images
    #  실제로 구현해야 하는 함수
    def _processing(self, file_lst: list) -> None:
        try:
            # 파일리스트가 비었으면 아무것도 하지 않는다.
            if not file_lst:
                return

            rel_base_path = os.path.dirname(file_lst[0])  # 웹툰이 저장되어 있는 폴더 경로
            base_path = os.path.abspath(rel_base_path)  # 절대경로로 변환
            print("기반 경로 : ", base_path)

            # output 이라는 문구가 포함된 모든 파일을 지우고 시작
            # 리스트와 파일 둘다 삭제를 반영해준다.

            output_path = os.path.join(base_path, 'output.png')
            # print("output_path : ", output_path)

            if os.path.isfile(output_path):
                os.remove(output_path)

            rel_output_path = os.path.join(rel_base_path, 'output.png')
            if rel_output_path in file_lst:
                file_lst.remove(rel_output_path)

            result = None

            img_lst = []
            for image_file in file_lst:
                # 소문자로 변환
                image_file = image_file.lower()

                # 이미지 읽기 (이미지 파일인경우만 수행)
                if image_file.endswith('.png') or image_file.endswith('.jpg') or image_file.endswith('.jpeg'):
                    print("이미지 파일 : ", image_file)
                    image_full_path = os.path.abspath(image_file)
                    # 한글 경로를 처리할 수 있게 numpy로 읽어옴
                    img_array = np.fromfile(image_full_path, np.uint8)
                    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                    img_lst.append(img)

            # call vconcat_resize_min function
            result = self.__vconcat_resize_min(img_lst)
            # result = cv2.vconcat(img_lst)

            output_path = os.path.join(base_path, 'output.png')
            print("출력 경로 : ", output_path)

            # imwrite 의 경우에도 한글 경로 인식이 안됨.

            extension = os.path.splitext(output_path)[1]  # 이미지 확장자

            result, encoded_img = cv2.imencode(extension, result)
            if result:
                with open(output_path, mode='w+b') as f:
                    encoded_img.tofile(f)
            # cv2.imwrite(output_path, result)
            print(f"병합 작업 완료 : {base_path}")

        except Exception as e:
            raise e

    # 디렉토리에서 목록 읽고 리스트로 return
    def __get_files_in_dir(self, path):
        file_lst = os.listdir(path)
        for i in range(0, len(file_lst)):
            file_lst[i] = os.path.join(path, file_lst[i])
        file_lst = natsort.natsorted(file_lst)  # natural sort 로 정렬
        return file_lst

    # Public Method -------------------------------------------------------

    def print_lists(self) -> None:
        for element in self.__file_lst:
            print(element)

    def run(self) -> None:
        try:
            # 단일 디렉토리인 경우
            if self.__pure_file:
                self._processing(self.__file_lst)  # 파일 리스트 그대로 merge
            else:
                # 폴더가 안에 또 있는 구조면
                for dir in self.__file_lst:
                    inner_files_lst = self.__get_files_in_dir(dir)
                    self._processing(inner_files_lst)
        except Exception as e:
            print(e)
