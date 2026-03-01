"""
Base JSON:API schemas.
"""

from __future__ import annotations

from dataclasses import dataclass
from inspect import isclass
from types import GenericAlias
from typing import TYPE_CHECKING, Any, Callable, Optional, Sequence, Type, Union, get_args

from pydantic import BaseModel, ConfigDict, Field

# noinspection PyProtectedMember
from pydantic._internal._typing_extra import is_none_type

# noinspection PyProtectedMember
from pydantic.fields import FieldInfo

from django_ninja_jsonapi.common import search_relationship_info
from django_ninja_jsonapi.types_metadata import RelationshipInfo

if TYPE_CHECKING:
    from django_ninja_jsonapi.data_typing import TypeSchema


class BaseJSONAPIRelationshipSchema(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    id: str = Field(default=..., description="Related object ID")
    type: str = Field(default=..., description="Type of the related resource object")


class BaseJSONAPIRelationshipDataToOneSchema(BaseModel):
    data: BaseJSONAPIRelationshipSchema
    links: Optional[dict[str, Any]] = None


class BaseJSONAPIRelationshipDataToManySchema(BaseModel):
    data: list[BaseJSONAPIRelationshipSchema]
    links: Optional[dict[str, Any]] = None


class BaseJSONAPIItemSchema(BaseModel):
    """Base JSON:API item schema."""

    type: str = Field(description="Resource type")
    attributes: dict = Field(description="Resource object attributes")
    links: Optional[dict[str, Any]] = Field(default=None, description="Resource links")
    meta: Optional[dict[str, Any]] = Field(default=None, description="Resource meta")


class BaseJSONAPIItemInSchema(BaseJSONAPIItemSchema):
    """
    Schema for post/patch method.

    Post: optionally accept custom id via ClientCanSetId metadata.
    Patch: id is required to identify the resource being updated.
    """

    attributes: TypeSchema = Field(description="Resource object attributes")
    relationships: Optional[TypeSchema] = Field(default=None, description="Resource object relationships")
    id: Optional[str] = Field(description="Resource object ID")


class BaseJSONAPIDataInSchema(BaseModel):
    data: BaseJSONAPIItemInSchema


class BaseJSONAPIObjectSchema(BaseJSONAPIItemSchema):
    """Base JSON:API object schema."""

    id: str = Field(description="Resource object ID")


class JSONAPIResultListMetaSchema(BaseModel):
    """JSON:API list meta schema."""

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )

    count: Optional[int]
    total_pages: Optional[int] = Field(alias="totalPages")


class JSONAPIDocumentObjectSchema(BaseModel):
    """
    JSON:API Document Object Schema.

    https://jsonapi.org/format/#document-jsonapi-object
    """

    version: str = Field(default="1.0", description="json-api версия")


class JSONAPIObjectSchema(BaseJSONAPIObjectSchema):
    """JSON:API base object schema."""

    model_config = ConfigDict(
        from_attributes=True,
    )


class BaseJSONAPIResultSchema(BaseModel):
    """
    JSON:API Required fields schema
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    jsonapi: Optional[JSONAPIDocumentObjectSchema] = Field(default=None, description="JSON:API version object")
    meta: Optional[JSONAPIResultListMetaSchema] = Field(default=None, description="JSON:API metadata")
    links: Optional[dict[str, Any]] = Field(default=None, description="Top level document links")


class JSONAPIResultListSchema(BaseJSONAPIResultSchema):
    """JSON:API list base result schema."""

    data: Sequence[JSONAPIObjectSchema] = Field(description="Resource objects collection")


class JSONAPIResultDetailSchema(BaseJSONAPIResultSchema):
    """JSON:API base detail schema."""

    data: JSONAPIObjectSchema = Field(description="Resource object data")


RelationshipInfoSchema = Union[
    Type[BaseJSONAPIRelationshipDataToOneSchema],
    Type[BaseJSONAPIRelationshipDataToManySchema],
]


class JSONAPISchemaIntrospectionError(Exception):
    pass


# Note: when 3.9 support is dropped, add `slots=True` to JSONAPIObjectSchemas dataclass


@dataclass(frozen=True)
class JSONAPIObjectSchemas:
    attributes_schema: Type[BaseModel]
    relationships_schema: Type[BaseModel]
    object_jsonapi_schema: Type[JSONAPIObjectSchema]
    can_be_included_schemas: dict[str, Type[JSONAPIObjectSchema]]

    @property
    def included_schemas_list(self) -> list[Type[JSONAPIObjectSchema]]:
        return list(self.can_be_included_schemas.values())


@dataclass(frozen=True)
class BuiltSchemasDTO:
    schema_in_post: Type[BaseJSONAPIDataInSchema]
    schema_in_post_data: Type[BaseJSONAPIItemInSchema]
    schema_in_patch: Type[BaseJSONAPIDataInSchema]
    schema_in_patch_data: Type[BaseJSONAPIItemInSchema]
    detail_response_schema: Type[JSONAPIResultDetailSchema]
    list_response_schema: Type[JSONAPIResultListSchema]


FieldValidators = dict[str, Callable]


@dataclass(frozen=True)
class SchemasInfoDTO:
    # id field
    resource_id_field: tuple[Any, Any, Any, Any]
    # pre-built attributes
    attributes_schema: Type[BaseModel]
    # relationships
    relationships_schema: Type[BaseModel]
    # has any required relationship
    has_required_relationship: bool
    # anything that can be included
    included_schemas: list[tuple[str, Type[BaseModel], str]]

    relationships_info: dict[str, tuple[RelationshipInfo, Any]]

    field_schemas: dict[str, Type[BaseModel]]

    model_validators: dict

    meta_fields: list[str]


def get_model_field(schema: Type["TypeSchema"], field: str) -> str:
    """
    Get the model field of a schema field.

    For example:

    class Computer:
        user = relationship(User)

    class ComputerSchema(pydantic_base):
        owner = Field(alias="user", relationship=...)

    :param schema: a pydantic schema
    :param field: the name of the schema field
    :return: the name of the field in the model
    :raises Exception: if the schema from parameter has no attribute for parameter.
    """
    if schema.model_fields.get(field) is None:
        msg = f"{schema.__name__} has no attribute {field}"
        raise JSONAPISchemaIntrospectionError(msg)
    return field


def get_relationship_fields_names(schema: Type["TypeSchema"]) -> set[str]:
    """
    Return relationship fields of a schema.

    :param schema: a schemas schema
    """
    names: set[str] = set()
    for i_name, i_type in schema.model_fields.items():
        if search_relationship_info.first(i_type):
            names.add(i_name)
    return names


def get_schema_from_type(resource_type: str, schemas: dict[str, Type[BaseModel]]) -> Type[BaseModel]:
    """
    Retrieve a schema from the registry by his type.

    :param resource_type: the type of the resource.
    :param schemas: mapping of resource type to schema.
    :return Schema: the schema class.
    :raises Exception: if the schema not found for this resource type.
    """
    try:
        return schemas[resource_type]
    except KeyError as ex:
        msg = f"Couldn't find schema for type: {resource_type}"
        raise Exception(msg) from ex


def get_schema_from_field_annotation(field: FieldInfo) -> Optional[Type[TypeSchema]]:
    annotation_ = field.annotation

    if isclass(annotation_) and issubclass(annotation_, BaseModel):
        return annotation_

    choices = list(get_args(field.annotation))
    while choices:
        elem = choices.pop(0)
        if isinstance(elem, GenericAlias):
            choices.extend(get_args(elem))
            continue

        if is_none_type(elem):
            continue

        if isclass(elem) and issubclass(elem, BaseModel):
            return elem

    return None


def get_related_schema(schema: Type[TypeSchema], field: str) -> Type[TypeSchema]:
    """
    Retrieve the related schema of a relationship field.

    :params schema: the schema to retrieve le relationship field from
    :params field: the relationship field
    :return: the related schema
    """
    result = get_schema_from_field_annotation(schema.model_fields[field])
    assert result is not None
    return result
