import json
from typing import List, Literal, Optional
from dataclasses import dataclass
from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class AuthorBase:
    id: Optional[int] = None
    name: Optional[str] = None


@dataclass_json
@dataclass
class Author:
    writers: Optional[List[AuthorBase]] = None
    painters: Optional[List[AuthorBase]] = None
    originAuthors: Optional[List[AuthorBase]] = None


@dataclass_json
@dataclass
class Age:
    type: Optional[Literal['RATE_12', 'RATE_15', 'RATE_18']] = None
    description: Optional[str] = None


@dataclass_json
@dataclass
class Article:
    no: Optional[int] = None
    subtitle: Optional[str] = None
    charge: Optional[bool] = None


@dataclass_json
@dataclass
class CurationTag:
    id: Optional[int] = None
    tagName: Optional[str] = None
    urlPath: Optional[str] = None
    curationType: Optional[str] = None

# 메인으로 사용할 Webtoon 클래스 정의 (생략된 부분은 ... 으로 표시)


@dataclass_json
@dataclass
class NWebtoonMainData:
    titleId: Optional[int] = None
    thumbnailUrl: Optional[str] = None
    sharedThumbnailUrl: Optional[str] = None
    titleName: str = ""
    webtoonLevelCode: Literal['WEBTOON',
                              'CHALLENGE', 'BEST_CHALLENGE'] = "WEBTOON"
    author: Optional[Author] = None
    age: Optional[Age] = None
    publishDescription: Optional[str] = None
    synopsis: str = ""
    favoriteCount: Optional[int] = None
    favorite: Optional[bool] = None
    latestReadArticle: Optional[Article] = None
    firstArticle: Optional[Article] = None
    rest: Optional[bool] = None
    finished: Optional[bool] = None
    dailyPass: Optional[bool] = None
    chargeBestChallenge: Optional[bool] = None
    contentsNo: Optional[int] = None
    new: Optional[bool] = None
    publishDayOfWeekList: Optional[list[str]] = None
    curationTagList: Optional[list[CurationTag]] = None
    adBannerList: Optional[list[dict]] = None

# json 모듈을 이용하여 JSON 문자열을 파이썬 딕셔너리로 변환


# with open('./type/test.json', encoding='utf-8') as f:
#     data = json.load(f)

# # str_json = json.dump(data)

# # .from_dict() 메서드를 이용하여 딕셔너리를 Webtoon 객체로 변환

# webtoon: NWebtoonMainData = NWebtoonMainData.from_dict(data)  # type: ignore

# # . 연산자로 nesting 되어 있는 속성들에 접근 가능

# print(webtoon.thumbnailUrl)  # H.C
