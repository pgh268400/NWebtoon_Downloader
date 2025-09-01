import json
from typing import List
from pydantic import BaseModel, Field

from type.api_article_list_info import Age, Author


class SearchView(BaseModel):
    titleId: int = 0
    titleName: str = ""
    webtoonLevelCode: str = ""
    thumbnailUrl: str = ""
    displayAuthor: str = ""
    author: Author = Field(default_factory=Author)
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
    tagList: List[str] = Field(default_factory=list)
    genreList: List[Age] = Field(default_factory=list)
    new: bool = False


class SearchBestChallenge(BaseModel):
    totalCount: int = 0
    searchViewList: List[SearchView] = Field(default_factory=list)


class SearchNbooksComic(SearchBestChallenge):
    pass


class SearchWebtoon(SearchBestChallenge):
    pass


class SearchChallenge(SearchBestChallenge):
    pass


class SearchNbooksNovel(SearchBestChallenge):
    pass


class NWebtoonSearchData(BaseModel):
    searchWebtoonResult: SearchWebtoon = Field(default_factory=SearchWebtoon)
    searchBestChallengeResult: SearchBestChallenge = Field(
        default_factory=SearchBestChallenge
    )
    searchChallengeResult: SearchChallenge = Field(default_factory=SearchChallenge)
    searchNbooksComicResult: SearchNbooksComic = Field(
        default_factory=SearchNbooksComic
    )
    searchNbooksNovelResult: SearchNbooksNovel = Field(
        default_factory=SearchNbooksNovel
    )

    # 기존 호출부 유지: dataclasses_json의 .from_dict 대체
    @classmethod
    def from_dict(cls, data: dict):
        return cls.model_validate(data)


if __name__ == "__main__":
    with open("./type/test2.json", encoding="utf-8") as f:
        data = json.load(f)

    # str_json = json.dump(data)

    # .from_dict() 메서드를 이용하여 딕셔너리를 Webtoon 객체로 변환

    webtoon: NWebtoonSearchData = NWebtoonSearchData.from_dict(data)  # type: ignore

    print(webtoon.searchBestChallengeResult)
