from enum import auto
import json
from typing import List, Any, Dict
from pydantic import BaseModel, Field, ConfigDict
from type.str_enum import StrEnum

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


class AuthorBase(BaseModel):
    id: int = 0
    name: str = ""

    # 동적 필드 처리를 위한 설정
    model_config = ConfigDict(extra="ignore")


class Author(BaseModel):
    writers: List[AuthorBase] = Field(default_factory=list)
    painters: List[AuthorBase] = Field(default_factory=list)
    originAuthors: List[AuthorBase] = Field(default_factory=list)

    # 동적 필드 처리를 위한 설정
    model_config = ConfigDict(extra="ignore")


class Age(BaseModel):
    type: str = (
        ""  # 몇 세 이용가인지. ["RATE_12", "RATE_15", "RATE_18", "NONE"] 로 추정되나, 이 4가지 type으로 정의 되지 않는 경우도 있어서 그냥 str로 정의
    )
    description: str = ""

    # 동적 필드 처리를 위한 설정
    model_config = ConfigDict(extra="ignore")


class Article(BaseModel):
    no: int = 0
    subtitle: str = ""
    charge: bool = False

    # 동적 필드 처리를 위한 설정
    model_config = ConfigDict(extra="ignore")


class CurationTag(BaseModel):
    id: int = 0
    tagName: str = ""
    urlPath: str = ""
    curationType: str = ""

    # 동적 필드 처리를 위한 설정
    model_config = ConfigDict(extra="ignore")


class GfpAdCustomParam(BaseModel):
    """광고 관련 커스텀 파라미터"""

    titleId: int = 0
    webtoonLevelCode: str = ""
    titleName: str = ""
    displayAuthor: str = ""
    genreTypes: List[str] = Field(default_factory=list)
    rankGenreTypes: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    weekdays: List[str] = Field(default_factory=list)
    finishedYn: str = "N"
    adultYn: str = "N"
    dailyPlusYn: str = "N"
    dailyFreeYn: str = "N"

    # 동적 필드 처리를 위한 설정
    model_config = ConfigDict(extra="ignore")


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
    gfpAdCustomParam: GfpAdCustomParam = Field(default_factory=GfpAdCustomParam)

    # 동적 필드 처리를 위한 설정
    model_config = ConfigDict(
        extra="allow",  # 정의되지 않은 필드도 허용
        validate_assignment=True,  # 할당 시 검증
        arbitrary_types_allowed=True,  # 임의의 타입 허용
    )

    # 동적 필드를 저장할 딕셔너리
    extra_fields: Dict[str, Any] = Field(default_factory=dict)

    # 기존 호출부 유지: dataclasses_json의 .from_dict 대체
    @classmethod
    def from_dict(cls, data: dict):
        return cls.model_validate(data)

    def model_post_init(self, __context: Any) -> None:
        """모델 초기화 후 실행되는 메서드 - 동적 필드 처리"""
        # 정의되지 않은 필드들을 extra_fields에 저장
        if hasattr(self, "__pydantic_extra__"):
            self.extra_fields = self.__pydantic_extra__ or {}


# 직접 실행했을때만 실행되는 코드 (import 되었을때는 실행되지 않음, 모듈 단위 테스트용)
if __name__ == "__main__":
    # json 모듈을 이용하여 JSON 문자열을 파이썬 딕셔너리로 변환

    with open("./type/test.json", encoding="utf-8") as f:
        data = json.load(f)

    # str_json = json.dump(data)

    # .from_dict() 메서드를 이용하여 딕셔너리를 Webtoon 객체로 변환

    webtoon: NWebtoonMainData = NWebtoonMainData.from_dict(data)

    # . 연산자로 nesting 되어 있는 속성들에 접근 가능

    print(webtoon.thumbnailUrl)  # H.C

    # 동적 필드 테스트
    print("Extra fields:", webtoon.extra_fields)
