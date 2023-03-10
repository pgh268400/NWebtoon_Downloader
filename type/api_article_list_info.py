from typing import List, Literal
from dataclasses import dataclass


@dataclass
class Writer:
    id: int
    name: str


@dataclass
class Painter:
    id: int
    name: str


@dataclass
class OriginAuthor:
    id: int
    name: str


@dataclass
class Age(dict):
    type: str
    description: str

    # 딕셔너리를 Age 객체로 변환하는 메소드
    @classmethod
    def from_dict(cls, age_dict):
        return cls(age_dict['type'], age_dict['description'])


@dataclass
class DailyToon:
    no: int
    subtitle: str
    charge: bool


@dataclass
class CurationTag:
    id: int
    tagName: str
    urlPath: str
    curationType: str


@dataclass
class NWebtoonData:
    titleId: int
    thumbnailUrl: str
    sharedThumbnailUrl: str
    titleName: str
    webtoonLevelCode: Literal['WEBTOON', 'CHALLENGE', 'BEST_CHALLENGE']
    author: dict[List[Writer], List[Painter], List[OriginAuthor]]
    thumbnailBadgeList: List[dict]
    age: Age
    publishDescription: str
    synopsis: str
    favoriteCount: int
    favorite: bool
    firstArticle: DailyToon
    publishDayOfWeekList: List[str]
    rest: bool
    finished: bool
    dailyPass: bool
    curationTagList: List[CurationTag]
    adBannerList: List[dict]
    chargeBestChallenge: bool
    contentsNo: int
    new: bool
    latestReadArticle: DailyToon = None

    # NWebtoonData 객체 생성 이후에 age 인스턴스를 Age 객체로 자동 변환 (딕셔너리에서 . 연산자를 통해 접근할 수 있도록 허용)
    def __post_init__(self):
        if isinstance(self.age, dict):
            self.age = Age.from_dict(self.age)


"""
API EXAMPLE
https://comic.naver.com/api/article/list/info?titleId=805671
{
	"titleId": 805671,
	"thumbnailUrl": "https://image-comic.pstatic.net/webtoon/805671/thumbnail/thumbnail_IMAG21_8be4a557-d691-48b1-8445-199e6c0c5dbd.jpg",
	"sharedThumbnailUrl": "https://shared-comic.pstatic.net/thumb/webtoon/805671/thumbnail/thumbnail_IMAG19_084e60db-c6e9-4abc-a55b-13288b82cd35.jpg",
	"titleName": "공작저의 붉은 밤",
	"webtoonLevelCode": "WEBTOON",
	"author": {
		"writers": [{
			"id": 354675,
			"name": "H.C"
		}],
		"painters": [{
			"id": 360889,
			"name": "타샤토토"
		}],
		"originAuthors": [{
			"id": 360890,
			"name": "유세라"
		}]
	},
	"thumbnailBadgeList": [],
	"age": {
		"type": "RATE_15",
		"description": "15세 이용가"
	},
	"publishDescription": "화요웹툰",
	"synopsis": "\"피곤하겠지만, 혼인신고부터 합시다.\" \n다짜고짜 찾아와 결혼을 하자는 뱀파이어! \n이게 바로, 아빠의 숨겨진 계획!? \n갑작스럽게 남편이 생긴 것도 모자라, \n어마어마한 유산의 주인공이 된 시골 소녀, 소렐. \n얼떨결에 대학 생활과 신혼을 함께 보내게 생겼다. \n숨겨진 대마법사의 딸과 젠틀 뱀파이어의 붉은빛 신혼 일기!",
	"favoriteCount": 14225,
	"favorite": false,
	"latestReadArticle": {
		"no": 5,
		"subtitle": "5화",
		"charge": false
	},
	"firstArticle": {
		"no": 1,
		"subtitle": "1화",
		"charge": false
	},
	"publishDayOfWeekList": ["TUESDAY"],
	"rest": false,
	"finished": false,
	"dailyPass": false,
	"curationTagList": [{
		"id": 805671,
		"tagName": "로맨스",
		"urlPath": "/webtoon?tab=genre&genre=PURE",
		"curationType": "GENRE_PURE"
	}, {
		"id": 64,
		"tagName": "선결혼후연애",
		"urlPath": "/curation/list?type=CUSTOM_TAG&id=64",
		"curationType": "CUSTOM_TAG"
	}, {
		"id": 55,
		"tagName": "뱀파이어",
		"urlPath": "/curation/list?type=CUSTOM_TAG&id=55",
		"curationType": "CUSTOM_TAG"
	}, {
		"id": 51,
		"tagName": "로판",
		"urlPath": "/curation/list?type=CUSTOM_TAG&id=51",
		"curationType": "CUSTOM_TAG"
	}, {
		"id": 42,
		"tagName": "구원서사",
		"urlPath": "/curation/list?type=CUSTOM_TAG&id=42",
		"curationType": "CUSTOM_TAG"
	}, {
		"id": 805671,
		"tagName": "소설원작",
		"urlPath": "/curation/list?type=NOVEL_ORIGIN",
		"curationType": "NOVEL_ORIGIN"
	}],
	"adBannerList": [],
	"chargeBestChallenge": false,
	"contentsNo": 495212,
	"new": false
}
"""
