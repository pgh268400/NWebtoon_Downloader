import json
from typing import List, Optional
from dataclasses import dataclass, field
from dataclasses_json import dataclass_json

from type.api_article_list_info import Age, Author


@dataclass_json
@dataclass
class searchView:
    titleId: int = 0
    titleName: str = ""
    webtoonLevelCode: str = ""
    thumbnailUrl: str = ""
    displayAuthor: str = ""
    author: Author = Author()
    synopsis: str = ""
    finished: bool = False
    adult: bool = False
    nineteen: bool = False
    bm: bool = False
    up: bool = False
    rest: bool = False
    webtoonLevelUp: bool = False
    bestChallengeLevelUp: bool = False
    potenUp: bool = False
    articleTotalCount: int = 0
    lastArticleServiceDate: str = ""
    tagList: List[str] = field(default_factory=list)
    genreList: List[Age] = field(default_factory=list)
    new: bool = False


@dataclass_json
@dataclass
class searchBestChallenge:
    totalCount: int = 0
    searchViewList: List[searchView] = field(default_factory=list)


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
    searchWebtoonResult: searchWebtoon = searchWebtoon()
    searchBestChallengeResult: searchBestChallenge = searchBestChallenge()
    searchChallengeResult: searchChallenge = searchChallenge()
    searchNbooksComicResult: searchNbooksComic = searchNbooksComic()
    searchNbooksNovelResult: searchNbooksNovel = searchNbooksNovel()


if __name__ == "__main__":
    with open('./type/test2.json', encoding='utf-8') as f:
        data = json.load(f)

    # str_json = json.dump(data)

    # .from_dict() 메서드를 이용하여 딕셔너리를 Webtoon 객체로 변환

    webtoon: NWebtoonSearchData = NWebtoonSearchData.from_dict(
        data)  # type: ignore

    print(webtoon.searchBestChallengeResult)
