import os

import np as np

from PIL import Image
import natsort
import glob

class ImageMerger:
    # 파이썬에서 private = 앞에 언더바 두개 (__)

    def __init__(self, dir_path):
        self.__dir_path = dir_path

        # 디렉토리를 순회하면서 리스트에 저장 (앞의 경로까지 다 저장)
        file_lst = os.listdir(self.__dir_path)
        for i in range(0, len(file_lst)):
            file_lst[i] = dir_path + "\\" + file_lst[i]

        # 파일 리스트 기억
        self.__file_lst = file_lst  # 파일 리스트 기억
        self.__file_lst = natsort.natsorted(self.__file_lst)  # natural sort 로 정렬

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

    def print_lists(self):
        for element in self.__file_lst:
            print(element)

    # 코드 참고 : https://stackoverflow.com/questions/53876007/how-to-vertically-merge-two-images

    def __image_merge(self, file_lst):
        try:
            base_path = os.path.dirname(file_lst[0]) #웹툰이 저장되어 있는 폴더 경로

            #output 이라는 문구가 포함된 모든 파일을 지우고 시작
            output_lst = glob.glob('output*.jpg')
            print(output_lst)

            img_lst = [Image.open(elem) for elem in file_lst]  # 이미지 Class 리스트로 변환
            min_img_width = min(i.width for i in img_lst)

            total_height = 0
            for i, img in enumerate(img_lst):
                # If the image is larger than the minimum width, resize it
                if img.width > min_img_width:
                    # 필터 있는 버전 (제일 품질 좋고 느린 필터, 너무 느려서 뺌)
                    # img_lst[i] = img.resize((min_img_width, int(img.height / img.width * min_img_width)),
                    #                         Resampling.LANCZOS)
                    
                    img_lst[i] = img.resize((min_img_width, int(img.height / img.width * min_img_width)))
                total_height += img_lst[i].height

            #jpeg 최대 허용 크기를 넘어섰으면 (65535 x 65535)
            # if total_height > 65535:
            #

            # I have picked the mode of the first image to be generic. You may have other ideas
            # Now that we know the total height of all of the resized images, we know the height of our final image
            img_merge = Image.new(img_lst[0].mode, (min_img_width, total_height))
            y = 0
            for img in img_lst:
                img_merge.paste(img, (0, y))

                y += img.height

            save_path = base_path + "\\" + 'output.jpg'
            img_merge.save(save_path)
            print(save_path + " 저장 완료")
            return True
        except Exception as e:
            raise e

    # 디렉토리에서 목록 읽고 리스트로 return
    def __get_files_in_dir(self, path):
        file_lst = os.listdir(path)
        for i in range(0, len(file_lst)):
            file_lst[i] = path + "\\" + file_lst[i]
        file_lst = natsort.natsorted(file_lst)  # natural sort 로 정렬
        return file_lst

    def merge(self):
        # 단일 디렉토리인 경우
        if self.__pure_file:
            self.__image_merge(self.__file_lst)  # 파일 리스트 그대로 merge
            print(self.__file_lst)
        else:
            # 폴더가 안에 또 있는 구조면
            for dir in self.__file_lst:
                inner_files_lst = self.__get_files_in_dir(dir)
                print(inner_files_lst)
                self.__image_merge(inner_files_lst)


path = r"your_path"
image_controller = ImageMerger(path)
image_controller.merge()
