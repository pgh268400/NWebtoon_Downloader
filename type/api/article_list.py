import json
from typing import List, Any, Dict
from pydantic import BaseModel, Field, ConfigDict

from type.api.comic_info import WebtoonCode


class ArticleItem(BaseModel):
    no: int = 0
    thumbnailUrl: str = ""
    subtitle: str = ""
    starScore: float = 0.0
    bgm: bool = False
    up: bool = False
    charge: bool = False
    serviceDateDescription: str = ""
    volumeNo: int = 0
    hasReadLog: bool = False
    recentlyReadLog: bool = False
    thumbnailClock: bool = False
    thumbnailLock: bool = False

    # 동적 필드 처리를 위한 설정
    model_config = ConfigDict(extra="ignore")


class PageInfo(BaseModel):
    totalRows: int = 0
    pageSize: int = 0
    indexSize: int = 0
    page: int = 0
    totalPages: int = 0
    startRowNum: int = 0
    lastPage: int = 0
    firstPage: int = 0
    endRowNum: int = 0
    rawPage: int = 0
    prevPage: int = 0
    nextPage: int = 0

    # 동적 필드 처리를 위한 설정
    model_config = ConfigDict(extra="ignore")


class NWebtoonArticleListData(BaseModel):
    titleId: int = 0
    webtoonLevelCode: WebtoonCode = WebtoonCode.WEBTOON
    totalCount: int = 0
    contentsNo: int = 0
    finished: bool = False
    dailyPass: bool = False
    chargeBestChallenge: bool = False
    articleList: List[ArticleItem] = Field(default_factory=list)
    chargeFolderArticleList: List[ArticleItem] = Field(default_factory=list)
    chargeFolderUp: bool = False
    pageInfo: PageInfo = Field(default_factory=PageInfo)
    sort: str = ""
    exceptBmBanner: bool = False

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
    with open("./models/article_list.json", encoding="utf-8") as f:
        data = json.load(f)

    # .from_dict() 메서드를 이용하여 딕셔너리를 ArticleList 객체로 변환
    article_list: NWebtoonArticleListData = NWebtoonArticleListData.from_dict(data)

    # . 연산자로 nesting 되어 있는 속성들에 접근 가능
    print(f"웹툰 ID: {article_list.titleId}")
    print(f"총 화수: {article_list.totalCount}")
    print(
        f"첫 번째 화 제목: {article_list.articleList[0].subtitle if article_list.articleList else 'N/A'}"
    )

    # 동적 필드 테스트
    print("Extra fields:", article_list.extra_fields)
