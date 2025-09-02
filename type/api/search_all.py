import json
from typing import List, Any, Dict
from pydantic import BaseModel, Field, ConfigDict

from type.api.comic_info import Author


class CurationTag(BaseModel):
    id: int = 0
    tagName: str = ""
    urlPath: str = ""
    curationType: str = ""

    # 동적 필드 처리를 위한 설정
    model_config = ConfigDict(extra="ignore")


class SearchGenre(BaseModel):
    type: str = ""
    description: str = ""

    # 동적 필드 처리를 위한 설정
    model_config = ConfigDict(extra="ignore")


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
    tagList: List[CurationTag] = Field(default_factory=list)
    genreList: List[SearchGenre] = Field(default_factory=list)
    new: bool = False

    # 동적 필드 처리를 위한 설정
    model_config = ConfigDict(
        extra="allow",  # 정의되지 않은 필드도 허용
        validate_assignment=True,
        arbitrary_types_allowed=True,
    )

    # 동적 필드를 저장할 딕셔너리
    extra_fields: Dict[str, Any] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        """모델 초기화 후 실행되는 메서드 - 동적 필드 처리"""
        # 정의되지 않은 필드들을 extra_fields에 저장
        if hasattr(self, "__pydantic_extra__"):
            self.extra_fields = self.__pydantic_extra__ or {}


class SearchBestChallenge(BaseModel):
    totalCount: int = 0
    searchViewList: List[SearchView] = Field(default_factory=list)

    # 동적 필드 처리를 위한 설정
    model_config = ConfigDict(
        extra="allow",
        validate_assignment=True,
        arbitrary_types_allowed=True,
    )

    # 동적 필드를 저장할 딕셔너리
    extra_fields: Dict[str, Any] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        """모델 초기화 후 실행되는 메서드 - 동적 필드 처리"""
        if hasattr(self, "__pydantic_extra__"):
            self.extra_fields = self.__pydantic_extra__ or {}


# ... = pass랑 똑같은거
class SearchNbooksComic(SearchBestChallenge): ...


class SearchWebtoon(SearchBestChallenge): ...


class SearchChallenge(SearchBestChallenge): ...


class SearchNbooksNovel(SearchBestChallenge): ...


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

    # 동적 필드 처리를 위한 설정
    model_config = ConfigDict(
        extra="allow",  # 정의되지 않은 필드도 허용
        validate_assignment=True,
        arbitrary_types_allowed=True,
    )

    # 동적 필드를 저장할 딕셔너리
    extra_fields: Dict[str, Any] = Field(default_factory=dict)

    # 기존 호출부 유지: dataclasses_json의 .from_dict 대체
    @classmethod
    def from_dict(cls, data: dict):
        return cls.model_validate(data)

    def model_post_init(self, __context: Any) -> None:
        """모델 초기화 후 실행되는 메서드 - 동적 필드 처리"""
        if hasattr(self, "__pydantic_extra__"):
            self.extra_fields = self.__pydantic_extra__ or {}


# 더 유연한 동적 모델 (완전히 동적인 필드 처리)
class DynamicSearchData(BaseModel):
    """완전히 동적인 필드 처리를 위한 검색 데이터 모델"""

    model_config = ConfigDict(
        extra="allow",  # 모든 추가 필드 허용
        validate_assignment=True,
        arbitrary_types_allowed=True,
    )

    # 기본 필드들 (선택적)
    searchWebtoonResult: dict = Field(
        default_factory=dict, description="웹툰 검색 결과"
    )
    searchBestChallengeResult: dict = Field(
        default_factory=dict, description="베스트 챌린지 검색 결과"
    )

    def get_extra_field(self, field_name: str, default: Any = None) -> Any:
        """동적 필드 값을 가져오는 메서드"""
        return getattr(self, field_name, default)

    def has_extra_field(self, field_name: str) -> bool:
        """동적 필드가 존재하는지 확인하는 메서드"""
        return hasattr(self, field_name)

    def get_all_extra_fields(self) -> Dict[str, Any]:
        """모든 동적 필드를 딕셔너리로 반환"""
        if hasattr(self, "__pydantic_extra__"):
            return self.__pydantic_extra__ or {}
        return {}


if __name__ == "__main__":
    with open("./type/test2.json", encoding="utf-8") as f:
        data = json.load(f)

    # str_json = json.dump(data)

    # .from_dict() 메서드를 이용하여 딕셔너리를 Webtoon 객체로 변환

    webtoon: NWebtoonSearchData = NWebtoonSearchData.from_dict(data)

    print(webtoon.searchBestChallengeResult)

    # 동적 필드 테스트
    print("Extra fields:", webtoon.extra_fields)
