from enum import auto
import json
from typing import List, Literal
from pydantic import BaseModel, Field
from type.nwebtoon import StrEnum

"""
기존에 dataclass <-> json 변환간 사용하던 dataclasses_json 라이브러리가 파이썬 최신 버전에서 제대로 유지 보수 되지 않는걸 확인
dataclasses_json -> pydantic으로 마이그레이션.

GPT5의 설명 (검증 필요):
Pydantic은 JSON 같은 외부 데이터를 받아올 때 타입 검증과 자동 변환을 해주는 라이브러리입니다.
dataclass처럼 필드를 정의하지만 BaseModel을 상속하면 검사·변환·직렬화가 자동으로 처리됩니다.
즉, 데이터 모델링 + 타입 안전성 + 직렬화를 한 번에 해결해주는 도구입니다.

원래라면 @dataclass 데코레이터를 붙여서 타입들을 정의해주고 거기에 데이터 타입 검증 (validation), 변환 이런 것을 일일히
구현해야 했다면 Pydantic 을 사용하면 BaseModel 만 상속하면 이런것들이 다 딸려들어와서 타입 검증도 쉽게 하고, class-json 데이터간
변환도 쉽게 한다고 이해하면 될 거 같다.
"""


class WebtoonCode(StrEnum):
    WEBTOON = auto()
    CHALLENGE = auto()
    BEST_CHALLENGE = auto()


class WebtoonType(StrEnum):
    webtoon = auto()
    challenge = auto()
    bestChallenge = auto()


class AuthorBase(BaseModel):
    id: int = 0
    name: str = ""


class Author(BaseModel):
    writers: List[AuthorBase] = Field(default_factory=list)
    painters: List[AuthorBase] = Field(default_factory=list)
    originAuthors: List[AuthorBase] = Field(default_factory=list)


class Age(BaseModel):
    type: Literal["RATE_12", "RATE_15", "RATE_18"] = "RATE_12"
    description: str = ""


class Article(BaseModel):
    no: int = 0
    subtitle: str = ""
    charge: bool = False


class CurationTag(BaseModel):
    id: int = 0
    tagName: str = ""
    urlPath: str = ""
    curationType: str = ""


class NWebtoonMainData(BaseModel):
    titleId: int = 0
    thumbnailUrl: str = ""
    sharedThumbnailUrl: str = ""
    titleName: str = ""
    webtoonLevelCode: WebtoonCode = WebtoonCode.WEBTOON
    author: Author = Field(default_factory=Author)
    age: Age = Field(default_factory=Age)
    publishDescription: str = ""
    synopsis: str = ""
    favoriteCount: int = 0
    favorite: bool = False
    latestReadArticle: Article = Field(default_factory=Article)
    firstArticle: Article = Field(default_factory=Article)
    rest: bool = False
    finished: bool = False
    dailyPass: bool = False
    chargeBestChallenge: bool = False
    contentsNo: int = 0
    new: bool = False
    publishDayOfWeekList: List[str] = Field(default_factory=list)
    curationTagList: List[CurationTag] = Field(default_factory=list)
    adBannerList: List[dict] = Field(default_factory=list)

    # 기존 호출부 유지: dataclasses_json의 .from_dict 대체
    @classmethod
    def from_dict(cls, data: dict):
        return cls.model_validate(data)


# 직접 실행했을때만 실행되는 코드 (import 되었을때는 실행되지 않음, 모듈 단위 테스트용)
if __name__ == "__main__":
    # json 모듈을 이용하여 JSON 문자열을 파이썬 딕셔너리로 변환

    with open("./type/test.json", encoding="utf-8") as f:
        data = json.load(f)

    # str_json = json.dump(data)

    # .from_dict() 메서드를 이용하여 딕셔너리를 Webtoon 객체로 변환

    webtoon: NWebtoonMainData = NWebtoonMainData.from_dict(data)  # type: ignore

    # . 연산자로 nesting 되어 있는 속성들에 접근 가능

    print(webtoon.thumbnailUrl)  # H.C
