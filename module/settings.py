from enum import auto
import os
import configparser

from type.str_enum import StrEnum

# INI 파일을 쉽게 관리하기 위해
# 사용하는 클래스 (싱글톤?)


class FileSettingType(StrEnum):
    Folder = auto()
    Image = auto()


class Setting:
    def __init__(self, file_name="./settings.ini", encoding="UTF-8") -> None:
        try:
            # 세팅 파일 이름 설정
            self.__settings_path: str = file_name
            self.__encoding: str = encoding

            # 현재 실행 경로에 설정 파일이 없으면 기본값으로 생성한다.
            if not os.path.isfile(self.__settings_path):
                config = configparser.ConfigParser()
                config["ZeroFill"] = {}  # 섹션을 생성한다
                config["ZeroFill"]["Folder"] = "4"  # 섹션 아래 실제 값을 생성한다
                config["ZeroFill"]["Image"] = "4"

                config["Download"] = {}  # 다운로드 관련 설정 섹션
                config["Download"]["BatchSize"] = "5"  # 배치 크기
                config["Download"]["MaxConcurrent"] = "10"  # 최대 동시 다운로드 수
                config["Download"]["DelaySeconds"] = "1"  # 배치 간 대기 시간(초)

                # DEFAULT 섹션은 기본적으로 생성되어 있어 생성없이 쓸 수 있다
                config["DEFAULT"]["DownloadPath"] = "./Webtoon_Download"
                config["DEFAULT"]["ErrorPath"] = "./error_log.txt"

                # 실제 파일로 쓰기
                with open(
                    self.__settings_path, "w", encoding=self.__encoding
                ) as configfile:
                    config.write(configfile)

            # 설정 파일을 읽어서 객체 변수에 저장한다. (문자열)
            # 위에서 파일이 없으면 무조건 생성하므로, 여기선 파일이 존재한다고 확신할 수 있다.
            config = configparser.ConfigParser()
            config.read(self.__settings_path)

            self.__folder_zero_fill: int = int(config["ZeroFill"]["Folder"])
            self.__image_zero_fill: int = int(config["ZeroFill"]["Image"])
            self.__download_path: str = config["DEFAULT"]["DownloadPath"]
            self.__error_path: str = config["DEFAULT"]["ErrorPath"]

            # 다운로드 관련 설정값 읽기
            self.__batch_size: int = int(config["Download"]["BatchSize"])
            self.__max_concurrent: int = int(config["Download"]["MaxConcurrent"])
            self.__delay_seconds: float = float(config["Download"]["DelaySeconds"])

        except Exception as e:
            print(e)
            input(
                "INI 파일 처리 중 오류가 발생하였습니다. 업데이트 하셨다면 ini 파일을 삭제후 다시 실행해보세요."
            )
            # 프로그램 강제 종료
            os._exit(1)

    # 파이썬 기본 프로퍼티 타입에 호환이 안되므로 Getter 함수로 제작
    def get_zero_fill(self, type: FileSettingType) -> int:
        if type == FileSettingType.Folder:
            return self.__folder_zero_fill
        elif type == FileSettingType.Image:
            return self.__image_zero_fill

    @property
    def download_path(self) -> str:
        return self.__download_path

    @property
    def error_path(self) -> str:
        return self.__error_path

    @property
    def batch_size(self) -> int:
        return self.__batch_size

    @property
    def max_concurrent(self) -> int:
        return self.__max_concurrent

    @property
    def delay_seconds(self) -> float:
        return self.__delay_seconds


if __name__ == "__main__":
    s = Setting()
    print(s.get_zero_fill(FileSettingType.Folder))
    print(s.get_zero_fill(FileSettingType.Image))
