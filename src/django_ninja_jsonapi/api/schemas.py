from typing import Any, Iterable, Optional, Type

from pydantic import BaseModel

from django_ninja_jsonapi.data_typing import TypeModel, TypeSchema
from django_ninja_jsonapi.views.enums import Operation


class ResourceData(BaseModel):
    path: str
    tags: list[str]
    view: Type[Any]
    model: Type[TypeModel]
    source_schema: Type[TypeSchema]
    schema_in_post: Optional[Type[BaseModel]]
    schema_in_post_data: Type[BaseModel]
    schema_in_post_envelope: Type[BaseModel]
    schema_in_patch: Optional[Type[BaseModel]]
    schema_in_patch_data: Type[BaseModel]
    schema_in_patch_envelope: Type[BaseModel]
    detail_response_schema: Type[BaseModel]
    list_response_schema: Type[BaseModel]
    pagination_default_size: Optional[int] = 20
    pagination_default_number: Optional[int] = 1
    pagination_default_offset: Optional[int] = None
    pagination_default_limit: Optional[int] = None
    operations: Iterable[Operation] = ()
    ending_slash: bool = True
