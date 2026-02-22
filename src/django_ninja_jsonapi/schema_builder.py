"""JSON API schemas builder class."""

import logging
from typing import Annotated, Any, Callable, Literal, Optional, Type, TypeVar, Union

from pydantic import AfterValidator, BeforeValidator, ConfigDict, PlainValidator, WrapValidator, create_model
from pydantic import BaseModel as PydanticBaseModel

# noinspection PyProtectedMember
from pydantic.fields import FieldInfo

from django_ninja_jsonapi.common import get_relationship_info_from_field_metadata, search_client_can_set_id
from django_ninja_jsonapi.schema import (
    BaseJSONAPIDataInSchema,
    BaseJSONAPIItemInSchema,
    BaseJSONAPIRelationshipDataToManySchema,
    BaseJSONAPIRelationshipDataToOneSchema,
    BaseJSONAPIRelationshipSchema,
    BaseJSONAPIResultSchema,
    BuiltSchemasDTO,
    JSONAPIObjectSchema,
    JSONAPIObjectSchemas,
    JSONAPIResultDetailSchema,
    JSONAPIResultListSchema,
    RelationshipInfoSchema,
    SchemasInfoDTO,
    get_schema_from_field_annotation,
)
from django_ninja_jsonapi.schema_base import BaseModel, Field, registry
from django_ninja_jsonapi.storages.schemas_storage import schemas_storage
from django_ninja_jsonapi.types_metadata import RelationshipInfo
from django_ninja_jsonapi.validation_utils import extract_validators

log = logging.getLogger(__name__)
JSONAPIObjectSchemaType = TypeVar("JSONAPIObjectSchemaType", bound=PydanticBaseModel)


class SchemaBuilder:
    def __init__(
        self,
        resource_type: str,
    ):
        self._resource_type = resource_type

    def _create_schemas_objects_list(self, schema: Type[BaseModel]) -> Type[JSONAPIResultListSchema]:
        object_jsonapi_list_schema, list_jsonapi_schema = self.build_list_schemas(schema)
        # TODO: do we need this `object_jsonapi_list_schema` field? it's not used anywhere 🤔
        # self.object_jsonapi_list_schema: Type[JSONAPIObjectSchema] = object_jsonapi_list_schema
        return list_jsonapi_schema

    def _create_schemas_object_detail(self, schema: Type[BaseModel]) -> Type[JSONAPIResultDetailSchema]:
        object_jsonapi_detail_schema, detail_jsonapi_schema = self.build_detail_schemas(schema)
        # TODO: do we need this `object_jsonapi_detail_schema` field? it's not used anywhere 🤔
        # self.object_jsonapi_detail_schema: Type[JSONAPIObjectSchema] = object_jsonapi_detail_schema

        return detail_jsonapi_schema

    def create_schemas(
        self,
        schema: Type[BaseModel],
        schema_in_post: Optional[Type[BaseModel]] = None,
        schema_in_patch: Optional[Type[BaseModel]] = None,
    ) -> BuiltSchemasDTO:
        schema_in_post = schema_in_post or schema
        schema_name_in_post_suffix = ""

        if any(schema_in_post is cmp_schema for cmp_schema in [schema, schema_in_patch]):
            schema_name_in_post_suffix = "InPost"

        schema_in_patch = schema_in_patch or schema
        schema_name_in_patch_suffix = ""

        if any(schema_in_patch is cmp_schema for cmp_schema in [schema, schema_in_post]):
            schema_name_in_patch_suffix = "InPatch"

        schema_in_post, schema_in_post_data = self.build_schema_in(
            schema_in=schema_in_post,
            schema=schema,
            operation_type="create",
            schema_name_suffix=schema_name_in_post_suffix,
            non_optional_relationships=True,
        )

        schema_in_patch, schema_in_patch_data = self.build_schema_in(
            schema_in=schema_in_patch,
            schema=schema,
            operation_type="update",
            schema_name_suffix=schema_name_in_patch_suffix,
            id_field_required=True,
        )

        return BuiltSchemasDTO(
            schema_in_post=schema_in_post,
            schema_in_post_data=schema_in_post_data,
            schema_in_patch=schema_in_patch,
            schema_in_patch_data=schema_in_patch_data,
            list_response_schema=self._create_schemas_objects_list(schema),
            detail_response_schema=self._create_schemas_object_detail(schema),
        )

    def build_schema_in(
        self,
        schema_in: Type[BaseModel],
        schema,
        operation_type: Literal["create", "update", "get"],
        schema_name_suffix: str = "",
        non_optional_relationships: bool = False,
        id_field_required: bool = False,
    ) -> tuple[Type[BaseJSONAPIDataInSchema], Type[BaseJSONAPIItemInSchema]]:
        base_schema_name = schema_in.__name__.removesuffix("Schema") + schema_name_suffix

        dto = self.get_info_from_schema_for_building(
            base_name=base_schema_name,
            schema=schema_in,
            operation_type=operation_type,
            non_optional_relationships=non_optional_relationships,
        )

        object_jsonapi_schema = self.build_jsonapi_object(
            base_name=base_schema_name,
            resource_type=self._resource_type,
            dto=dto,
            model_base=BaseJSONAPIItemInSchema,
            id_field_required=id_field_required,
        )

        wrapped_object_jsonapi_schema = create_model(
            f"{base_schema_name}ObjectDataJSONAPI",
            data=(object_jsonapi_schema, ...),
            __base__=BaseJSONAPIDataInSchema,
        )

        schemas_storage.add_resource(
            builder=self,
            resource_type=self._resource_type,
            operation_type=operation_type,
            source_schema=schema,
            data_schema=object_jsonapi_schema,
            attributes_schema=dto.attributes_schema,
            field_schemas=dto.field_schemas,
            relationships_info=dto.relationships_info,
            model_validators=dto.model_validators,
            meta_fields=dto.meta_fields,
            schema_in=wrapped_object_jsonapi_schema,
        )

        return wrapped_object_jsonapi_schema, object_jsonapi_schema

    def _build_schema(
        self,
        base_name: str,
        schema: Type[BaseModel],
        builder: Callable,
    ):
        object_schemas = self.create_jsonapi_object_schemas(
            schema=schema,
            base_name=base_name,
            compute_included_schemas=True,
        )
        object_jsonapi_schema = object_schemas.object_jsonapi_schema
        response_jsonapi_schema = builder(
            name=base_name,
            object_jsonapi_schema=object_jsonapi_schema,
            includes_schemas=object_schemas.included_schemas_list,
        )
        return object_jsonapi_schema, response_jsonapi_schema

    def build_detail_schemas(
        self,
        schema: Type[BaseModel],
    ) -> tuple[Type[JSONAPIObjectSchema], Type[JSONAPIResultDetailSchema]]:
        return self._build_schema(
            base_name=f"{schema.__name__}Detail",
            schema=schema,
            builder=self.build_schema_for_detail_result,
        )

    def build_list_schemas(
        self,
        schema: Type[BaseModel],
    ) -> tuple[Type[JSONAPIObjectSchema], Type[JSONAPIResultListSchema]]:
        return self._build_schema(
            base_name=f"{schema.__name__}List",
            schema=schema,
            builder=self.build_schema_for_list_result,
        )

    @classmethod
    def _annotation_with_validators(cls, field: FieldInfo) -> type:
        annotation = field.annotation
        validators = []
        for val in field.metadata:
            if isinstance(val, (AfterValidator, BeforeValidator, WrapValidator, PlainValidator)):
                validators.append(val)

        if validators:
            annotation = Annotated.__class_getitem__((annotation, *validators))

        return annotation

    def get_info_from_schema_for_building(
        self,
        base_name: str,
        schema: Type[BaseModel],
        operation_type: Literal["create", "update", "get"],
        non_optional_relationships: bool = False,
    ) -> SchemasInfoDTO:
        attributes_schema_fields = {}
        relationships_schema_fields = {}
        relationships_info: dict[str, tuple[RelationshipInfo, Any]] = {}
        included_schemas: list[tuple[str, BaseModel, str]] = []
        has_required_relationship = False
        resource_id_field = (str, Field(default=None), None, {})
        meta_fields: list[str] = []

        for meta_attr in ("JSONAPIMeta", "Meta"):
            meta_obj = getattr(schema, meta_attr, None)
            if meta_obj is None:
                continue

            configured_meta_fields = getattr(meta_obj, "meta_fields", None)
            if configured_meta_fields:
                meta_fields = list(configured_meta_fields)
                break

        # required! otherwise we get ForwardRef
        schema.model_rebuild(_types_namespace=registry.schemas)
        for name, field in (schema.model_fields or {}).items():
            if relationship_info := get_relationship_info_from_field_metadata(field):
                relationships_info[name] = (relationship_info, field)
                relationship_schema = self.create_relationship_data_schema(
                    field_name=name,
                    base_name=base_name,
                    field=field,
                    operation_type=operation_type,
                    relationship_info=relationship_info,
                )
                field_marked_required = field.is_required()
                relationship_field = ... if (non_optional_relationships and field_marked_required) else None
                if relationship_field is not None:
                    has_required_relationship = True
                relationships_schema_fields[name] = (relationship_schema, relationship_field)
                # works both for to-one and to-many
                if related_schema := get_schema_from_field_annotation(field):
                    included_schemas.append((name, related_schema, relationship_info.resource_type))
            elif name == "id":
                id_validators, _ = extract_validators(
                    model=schema,
                    include_for_field_names={"id"},
                )

                if not (can_set_id := search_client_can_set_id.first(field)):
                    continue
                resource_id_field = (str, can_set_id, self._annotation_with_validators(field=field), id_validators)
            else:
                attributes_schema_fields[name] = (self._annotation_with_validators(field=field), field.default)

        model_config = ConfigDict(
            from_attributes=True,
        )

        field_validators, model_validators = extract_validators(schema, exclude_for_field_names={"id"})
        attributes_schema = create_model(
            f"{base_name}AttributesJSONAPI",
            **attributes_schema_fields,
            __config__=model_config,
            __validators__={**field_validators, **model_validators},
        )

        field_schemas = {}
        for field_name, field in attributes_schema_fields.items():
            field_validators, _ = extract_validators(
                schema,
                include_for_field_names={field_name},
            )
            field_schemas[field_name] = create_model(
                f"{base_name}{field_name.title()}AttributeJSONAPI",
                **{field_name: field},
                __config__=model_config,
                __validators__=field_validators,
            )

        relationships_schema = create_model(
            f"{base_name}RelationshipsJSONAPI",
            **relationships_schema_fields,
            __config__=model_config,
        )

        return SchemasInfoDTO(
            resource_id_field=resource_id_field,
            attributes_schema=attributes_schema,
            relationships_schema=relationships_schema,
            relationships_info=relationships_info,
            has_required_relationship=has_required_relationship,
            included_schemas=included_schemas,
            field_schemas=field_schemas,
            model_validators=model_validators,
            meta_fields=meta_fields,
        )

    @classmethod
    def create_relationship_schema(
        cls,
        name: str,
        relationship_info: RelationshipInfo,
    ) -> Type[BaseJSONAPIRelationshipSchema]:
        # TODO: cache?
        if name.endswith("s"):
            # plural to single
            name = name[:-1]

        return create_model(
            f"{name}RelationshipJSONAPI",
            id=(
                str,
                Field(
                    ...,
                    description="Resource object id",
                    json_schema_extra={"example": relationship_info.resource_id_example},
                ),
            ),
            type=(
                str,
                Field(
                    default=relationship_info.resource_type,
                    description="Resource type",
                ),
            ),
            __base__=BaseJSONAPIRelationshipSchema,
        )

    def create_relationship_data_schema(
        self,
        field_name: str,
        base_name: str,
        operation_type: Literal["create", "update", "get"],
        field: FieldInfo,
        relationship_info: RelationshipInfo,
    ) -> RelationshipInfoSchema:
        if relationship_schema := schemas_storage.get_relationship_schema(
            from_resource_type=self._resource_type,
            to_resource_type=relationship_info.resource_type,
            operation_type=operation_type,
            field_name=field_name,
        ):
            return relationship_schema

        base_name = base_name.removesuffix("Schema")
        schema_name = f"{base_name}{field_name.title()}"
        relationship_schema = self.create_relationship_schema(
            name=schema_name,
            relationship_info=relationship_info,
        )
        base = BaseJSONAPIRelationshipDataToOneSchema
        if relationship_info.many:
            relationship_schema = list[relationship_schema]
            base = BaseJSONAPIRelationshipDataToManySchema
        elif not field.is_required():
            relationship_schema = Optional[relationship_schema]

        relationship_data_schema = create_model(
            f"{schema_name}RelationshipDataJSONAPI",
            # TODO: on create (post request) sometimes it's required and at the same time on fetch it's not required
            data=(relationship_schema, Field(... if field.is_required() else None)),
            __base__=base,
        )

        schemas_storage.add_relationship(
            from_resource_type=self._resource_type,
            to_resource_type=relationship_info.resource_type,
            operation_type=operation_type,
            field_name=field_name,
            relationship_schema=relationship_data_schema,
            relationship_info=relationship_info,
        )
        return relationship_data_schema

    def build_jsonapi_object(
        self,
        base_name: str,
        resource_type: str,
        dto: SchemasInfoDTO,
        model_base: Type[JSONAPIObjectSchemaType] = JSONAPIObjectSchema,
        with_relationships: bool = True,
        id_field_required: bool = False,
    ) -> Type[JSONAPIObjectSchemaType]:
        field_type, can_set_id, id_cast_func, id_validators = dto.resource_id_field

        if can_set_id:
            field_type = Annotated[field_type, can_set_id]

        relationship_less_fields = {}
        relationship_less_fields.update(
            id=(field_type, Field(... if id_field_required else None)),
            attributes=(dto.attributes_schema, ...),
            type=(str, Field(default=resource_type or self._resource_type, description="Resource type")),
        )

        object_jsonapi_schema_fields = {}
        object_jsonapi_schema_fields.update(
            id=(field_type, Field(... if id_field_required else None)),
            attributes=(dto.attributes_schema, ...),
            type=(str, Field(default=resource_type or self._resource_type, description="Resource type")),
        )

        if with_relationships:
            object_jsonapi_schema_fields.update(
                relationships=(Optional[dto.relationships_schema], ... if dto.has_required_relationship else None),
            )

        object_jsonapi_schema = create_model(
            f"{base_name}ObjectJSONAPI",
            **object_jsonapi_schema_fields,
            __validators__=id_validators,
            __base__=model_base,
        )

        return object_jsonapi_schema

    def find_all_included_schemas(
        self,
        included_schemas: list[tuple[str, BaseModel, str]],
    ) -> dict[str, Type[JSONAPIObjectSchema]]:
        return {
            name: self.create_jsonapi_object_schemas(
                included_schema,
                resource_type=resource_type,
            ).object_jsonapi_schema
            for (name, included_schema, resource_type) in included_schemas
        }

    def create_jsonapi_object_schemas(
        self,
        schema: Type[BaseModel],
        resource_type: Optional[str] = None,
        base_name: str = "",
        compute_included_schemas: bool = False,
    ) -> JSONAPIObjectSchemas:
        resource_type = resource_type or self._resource_type

        if object_schema := schemas_storage.get_jsonapi_object_schema(
            source_schema=schema,
            resource_type=resource_type,
        ):
            return object_schema

        base_name = base_name or schema.__name__

        dto = self.get_info_from_schema_for_building(
            base_name=base_name,
            operation_type="get",
            schema=schema,
        )

        object_jsonapi_schema = self.build_jsonapi_object(
            base_name=base_name,
            resource_type=resource_type or self._resource_type,
            dto=dto,
        )
        relationship_less_object_jsonapi_schema = self.build_jsonapi_object(
            base_name=base_name,
            resource_type=resource_type or self._resource_type,
            dto=dto,
            with_relationships=False,
        )

        schemas_storage.add_resource(
            builder=self,
            resource_type=resource_type,
            operation_type="get",
            source_schema=schema,
            data_schema=relationship_less_object_jsonapi_schema,
            attributes_schema=dto.attributes_schema,
            field_schemas=dto.field_schemas,
            relationships_info=dto.relationships_info,
            model_validators=dto.model_validators,
            meta_fields=dto.meta_fields,
        )

        can_be_included_schemas = {}
        if compute_included_schemas:
            can_be_included_schemas = self.find_all_included_schemas(included_schemas=dto.included_schemas)

        result = JSONAPIObjectSchemas(
            attributes_schema=dto.attributes_schema,
            relationships_schema=dto.relationships_schema,
            object_jsonapi_schema=object_jsonapi_schema,
            can_be_included_schemas=can_be_included_schemas,
        )
        schemas_storage.add_jsonapi_object_schema(
            source_schema=schema,
            resource_type=resource_type,
            jsonapi_object_schema=result,
        )
        return result

    def build_schema_for_list_result(
        self,
        name: str,
        object_jsonapi_schema: Type[JSONAPIObjectSchema],
        includes_schemas: list[Type[JSONAPIObjectSchema]],
    ) -> Type[JSONAPIResultListSchema]:
        return self.build_schema_for_result(
            name=f"{name}JSONAPI",
            base=JSONAPIResultListSchema,
            data_type=list[object_jsonapi_schema],
            includes_schemas=includes_schemas,
        )

    def build_schema_for_detail_result(
        self,
        name: str,
        object_jsonapi_schema: Type[JSONAPIObjectSchema],
        includes_schemas: list[Type[JSONAPIObjectSchema]],
    ) -> Type[JSONAPIResultDetailSchema]:
        return self.build_schema_for_result(
            name=f"{name}JSONAPI",
            base=JSONAPIResultDetailSchema,
            data_type=object_jsonapi_schema,
            includes_schemas=includes_schemas,
        )

    @classmethod
    def build_schema_for_result(
        cls,
        name: str,
        base: Type[BaseJSONAPIResultSchema],
        data_type: Union[Type[JSONAPIObjectSchema], Type[list[JSONAPIObjectSchema]]],
        includes_schemas: list[Type[JSONAPIObjectSchema]],
    ) -> Union[Type[JSONAPIResultListSchema], Type[JSONAPIResultDetailSchema]]:
        included_schema_annotation = Union[JSONAPIObjectSchema]
        for includes_schema in includes_schemas:
            included_schema_annotation = Union[included_schema_annotation, includes_schema]

        schema_fields = {
            "data": (data_type, ...),
        }
        if includes_schemas:
            schema_fields.update(
                included=(
                    list[included_schema_annotation],
                    Field(default=None),
                ),
            )

        return create_model(
            name,
            **schema_fields,
            __base__=base,
        )
