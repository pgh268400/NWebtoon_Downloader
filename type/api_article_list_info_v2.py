import json
from typing import List, Literal
from dataclasses import dataclass, field
from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class AuthorBase:
    id: int = 0
    name: str = ""


@dataclass_json
@dataclass
class Author:
    writers: List[AuthorBase] = field(default_factory=list)
    painters: List[AuthorBase] = field(default_factory=list)
    originAuthors: List[AuthorBase] = field(default_factory=list)


@dataclass_json
@dataclass
class Age:
    type: Literal['RATE_12', 'RATE_15', 'RATE_18'] = 'RATE_12'
    description: str = ""


@dataclass_json
@dataclass
class Article:
    no: int = 0
    subtitle: str = ""
    charge: bool = False


@dataclass_json
@dataclass
class CurationTag:
    id: int = 0
    tagName: str = ""
    urlPath: str = ""
    curationType: str = ""


@dataclass_json
@dataclass
class NWebtoonMainData:
    titleId: int = 0
    thumbnailUrl: str = ""
    sharedThumbnailUrl: str = ""
    titleName: str = ""
    webtoonLevelCode: Literal['WEBTOON',
                              'CHALLENGE', 'BEST_CHALLENGE'] = "WEBTOON"
    author: Author = Author()
    age: Age = Age()
    publishDescription: str = ""
    synopsis: str = ""
    favoriteCount: int = 0
    favorite: bool = False
    latestReadArticle: Article = Article()
    firstArticle: Article = Article()
    rest: bool = False
    finished: bool = False
    dailyPass: bool = False
    chargeBestChallenge: bool = False
    contentsNo: int = 0
    new: bool = False
    publishDayOfWeekList: List[str] = field(default_factory=list)
    curationTagList: List[CurationTag] = field(default_factory=list)
    adBannerList: List[dict] = field(default_factory=list)


# 직접 실행했을때만 실행되는 코드 (import 되었을때는 실행되지 않음, 모듈 단위 테스트용)
if __name__ == "__main__":
    # json 모듈을 이용하여 JSON 문자열을 파이썬 딕셔너리로 변환

    with open('./type/test.json', encoding='utf-8') as f:
        data = json.load(f)

    # str_json = json.dump(data)

    # .from_dict() 메서드를 이용하여 딕셔너리를 Webtoon 객체로 변환

    webtoon: NWebtoonMainData = NWebtoonMainData.from_dict(  # type: ignore
        data)

    # . 연산자로 nesting 되어 있는 속성들에 접근 가능

    print(webtoon.thumbnailUrl)  # H.C
