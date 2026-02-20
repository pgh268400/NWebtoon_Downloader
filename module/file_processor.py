import re

# 폴더 / 파일 저장시 특수문자 저장용 처리 클래스

class FileProcessor:
    def remove_forbidden_str(self, string: str) -> str:
        """
        경로 금지 문자 제거, HTML문자 제거
        폴더에 들어갈 수 없는 특수문자를 들어갈 수 있는
        특수한 유니코드 문자 (겉보기에 똑같은 문자)로 치환 시킨다.
        윈도우에서는 시작/끝 공백문자가 금지되어있어 trim()도 같이 수행한다.
        """
        table = str.maketrans('\\/:*?"<>|..', "￦／：＊？＂˂˃｜․․")
        processed_string: str = string.translate(table)

        # \t 과 \n제거 (\t -> 공백 , \n -> 공백)
        table = str.maketrans("\t\n", "  ")
        processed_string = processed_string.translate(table)
        bprocessed_string = self.soft_strip_edges(processed_string)
        return bprocessed_string.strip().rstrip(".")

    def remove_tag(self, string: str) -> str:
        # <tag>, &nbfs 등등 제거
        cleaner = re.compile("<.*?>|&([a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});")
        string = re.sub(cleaner, "", string)
        return string

    def soft_strip_edges(self, s: str) -> str:
        # 경로명 앞 뒤 유니코드 공백 문자 제거
        WINDOWS_WEIRD_SPACES = [
            "\u00A0",  # NO-BREAK SPACE
            "\u200B",  # ZERO WIDTH SPACE
            "\u2009",  # THIN SPACE
            "\u200A",  # HAIR SPACE
            "\u3000",  # IDEOGRAPHIC SPACE
            "\uFEFF",  # ZERO WIDTH NO-BREAK SPACE (BOM)
        ]
        
        TRIM_CHARS = " \t\r\n" + "".join(WINDOWS_WEIRD_SPACES)
        return s.strip(TRIM_CHARS)
