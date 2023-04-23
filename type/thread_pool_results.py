# results = ThreadPool(thread_count).imap_unordered(self.p_image_download, self.get_image_link(start_index, end_index))
# 해당 ThreadPool 에서 results 로 반환하는 값은 self.p_image_download 의 반환값이다.
# self.p_image_download 의 반환 타입을 정의한다.

from typing import List, NamedTuple

# 이름을 가지는 튜플 타입 정의


class UrlPathTuple(NamedTuple):
    img_url: str = ""
    path: str = ""


# type alias : 복잡한 타입을 간단하게 이름으로 대체하는 것
# 여기선 List[UrlPath] 를 UrlPathList 로 대체한다.
UrlPathListResults = List[UrlPathTuple]
