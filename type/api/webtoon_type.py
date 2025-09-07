from enum import auto
from type.str_enum import StrEnum
from type.api.comic_info import WebtoonCode


class WebtoonType(StrEnum):
    webtoon = auto()
    challenge = auto()
    bestChallenge = auto()


# WEBTOON (API 코드) -> webtoon (URL/내부 문자열) 매핑
CODE_TO_TYPE = {
    WebtoonCode.WEBTOON: WebtoonType.webtoon,
    WebtoonCode.CHALLENGE: WebtoonType.challenge,
    WebtoonCode.BEST_CHALLENGE: WebtoonType.bestChallenge,
}


def to_webtoon_type(code: WebtoonCode) -> WebtoonType:
    """API의 WebtoonCode를 내부 WebtoonType으로 변환"""
    return CODE_TO_TYPE[code]


def to_url_segment_from_code(code: WebtoonCode) -> str:
    """WebtoonCode를 URL 세그먼트 문자열로 변환"""
    return CODE_TO_TYPE[code].value


def to_url_segment_from_type(wtype: WebtoonType) -> str:
    """WebtoonType을 URL 세그먼트 문자열로 변환"""
    return wtype.value
