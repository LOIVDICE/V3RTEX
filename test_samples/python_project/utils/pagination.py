from dataclasses import dataclass
from typing import List
from constants import DEFAULT_PAGE_SIZE


@dataclass
class PaginatedResult:
    items: list
    total: int
    page: int
    size: int

    @property
    def total_pages(self) -> int:
        return max(1, (self.total + self.size - 1) // self.size)

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages

    @property
    def has_prev(self) -> bool:
        return self.page > 1

    def to_dict(self) -> dict:
        return {
            "items": self.items,
            "total": self.total,
            "page": self.page,
            "size": self.size,
            "total_pages": self.total_pages,
            "has_next": self.has_next,
            "has_prev": self.has_prev,
        }


class Paginator:
    def __init__(self, page: int = 1, size: int = DEFAULT_PAGE_SIZE):
        self.page = max(1, page)
        self.size = size
        self.offset = (self.page - 1) * self.size

    def paginate(self, items: list, total: int) -> PaginatedResult:
        return PaginatedResult(items=items, total=total, page=self.page, size=self.size)
