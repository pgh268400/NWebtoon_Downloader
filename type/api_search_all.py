import json
from typing import List, Optional
from dataclasses import dataclass
from dataclasses_json import dataclass_json

from type.api_article_list_info_v2 import Age, Author


@dataclass_json
@dataclass
class searchView:
    titleId: Optional[int] = None
    titleName: Optional[str] = None
    webtoonLevelCode: Optional[str] = None
    thumbnailUrl: Optional[str] = None
    displayAuthor: Optional[str] = None
    author: Optional[Author] = None
    synopsis: Optional[str] = None
    finished: Optional[bool] = None
    adult: Optional[bool] = None
    nineteen: Optional[bool] = None
    bm: Optional[bool] = None
    up: Optional[bool] = None
    rest: Optional[bool] = None
    webtoonLevelUp: Optional[bool] = None
    bestChallengeLevelUp: Optional[bool] = None
    potenUp: Optional[bool] = None
    articleTotalCount: Optional[int] = None
    lastArticleServiceDate: Optional[str] = None
    tagList: Optional[List[str]] = None
    genreList: Optional[List[Age]] = None
    new: Optional[bool] = None


@dataclass_json
@dataclass
class searchBestChallenge:
    totalCount: Optional[int] = None
    searchViewList: Optional[List[searchView]] = None


@dataclass_json
@dataclass
class searchNbooksComic(searchBestChallenge):
    pass


@dataclass_json
@dataclass
class searchWebtoon(searchBestChallenge):
    pass


@dataclass_json
@dataclass
class searchChallenge(searchBestChallenge):
    pass


@dataclass_json
@dataclass
class searchNbooksNovel(searchBestChallenge):
    pass


@dataclass_json
@dataclass
class NWebtoonSearchData:
    searchWebtoonResult: Optional[searchWebtoon] = None
    searchBestChallengeResult: Optional[searchBestChallenge] = None
    searchChallengeResult: Optional[searchChallenge] = None
    searchNbooksComicResult: Optional[searchNbooksComic] = None
    searchNbooksNovelResult: Optional[searchNbooksNovel] = None


# with open('./type/test2.json', encoding='utf-8') as f:
#     data = json.load(f)

# # str_json = json.dump(data)

# # .from_dict() 메서드를 이용하여 딕셔너리를 Webtoon 객체로 변환

# webtoon: NWebtoonSearchData = NWebtoonSearchData.from_dict(data)

# print(webtoon.searchBestChallengeResult)
