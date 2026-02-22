# noinspection PyProtectedMember
from collections.abc import Generator
from typing import Generic, Optional, TypeVar

# noinspection PyProtectedMember
from pydantic.fields import FieldInfo

SearchType = TypeVar("SearchType")


class MetadataInstanceSearch(Generic[SearchType]):
    def __init__(self, search_type: type[SearchType]):
        self.search_type = search_type

    def iterate(self, field: FieldInfo) -> Generator[SearchType, None, None]:
        for elem in field.metadata:
            if isinstance(elem, self.search_type):
                yield elem

        return None

    def first(self, field: FieldInfo) -> Optional[SearchType]:
        return next(self.iterate(field), None)
