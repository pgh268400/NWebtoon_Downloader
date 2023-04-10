import os
import configparser
from typing import Literal

# INI 파일을 쉽게 관리하기 위해
# 사용하는 클래스 (싱글톤?)


class Setting:
    def __init__(self, file_name="./settings.ini", encoding="UTF-8") -> None:
        try:
            # 세팅 파일 이름 설정
            self.__settings_path: str = file_name
            self.__encoding: str = encoding

            # 현재 실행 경로에 설정 파일이 없으면 생성한다.
            if not os.path.isfile(self.__settings_path):
                config = configparser.ConfigParser()
                config['Folder'] = {}                # 섹션을 생성한다
                config['Image'] = {}

                config['Folder']['zerofill'] = '0'      # 섹션 아래 실제 값을 생성한다
                config['Image']['zerofill'] = '0'

                # DEFAULT 섹션은 기본적으로 생성되어 있어 생성없이 쓸 수 있다
                # config['DEFAULT']['DDD'] = 'EEE'

                # 실제 파일로 쓰기
                with open(self.__settings_path, 'w', encoding=self.__encoding) as configfile:
                    config.write(configfile)

            # 설정 파일을 읽어서 객체 변수에 저장한다. (문자열)
            # 위에서 파일이 없으면 무조건 생성하므로, 여기선 파일이 존재한다고 확신할 수 있다.
            config = configparser.ConfigParser()
            config.read(self.__settings_path)

            self.__folder_zero_fill: int = int(config['Folder']['zerofill'])
            self.__image_zero_fill: int = int(config['Image']['zerofill'])

        except Exception as e:
            print(e)
            input("INI 파일 처리 중 오류가 발생하였습니다.")
            # 프로그램 강제 종료
            os._exit(1)

    def get_zero_fill(self, type: Literal['Folder', 'Image']) -> int:
        if type == 'Folder':
            return self.__folder_zero_fill
        elif type == 'Image':
            return self.__image_zero_fill


if __name__ == "__main__":
    s = Setting()
    print(s.get_zero_fill('Folder'))
    print(s.get_zero_fill('Image'))
