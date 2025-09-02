from enum import Enum
from typing import Any


class StrEnum(str, Enum):
    def _generate_next_value_(name: str, start: int, count: int, last_values: list[Any]) -> str:
        return name

    def __repr__(self) -> str:
        return self.name

    def __str__(self) -> str:
        return self.name
