from collections import defaultdict
from typing import Any, Literal, Optional, Type

from django_ninja_jsonapi.data_typing import TypeSchema
from django_ninja_jsonapi.exceptions import InternalServerError
from django_ninja_jsonapi.schema import JSONAPIObjectSchemas
from django_ninja_jsonapi.types_metadata.relationship_info import RelationshipInfo


class SchemasStorage:
    def __init__(self):
        self._data: dict = {}
        self._source_schemas: dict[str, Type[TypeSchema]] = {}
        self._jsonapi_object_schemas: dict[tuple[Type[TypeSchema], str], JSONAPIObjectSchemas] = {}
        self._schema_in_keys: dict[str, str] = {
            "create": "schema_in_create",
            "update": "schema_in_update",
        }

    def _init_resource_if_needed(self, resource_type: str):
        if resource_type not in self._data:
            self._data[resource_type] = {
                "relationships": defaultdict(lambda: defaultdict(dict)),
            }

    def add_relationship(
        self,
        from_resource_type: str,
        to_resource_type: str,
        operation_type: Literal["create", "update", "get"],
        field_name: str,
        relationship_schema: Type[TypeSchema],
        relationship_info: RelationshipInfo,
    ):
        self._init_resource_if_needed(from_resource_type)
        relationships = self._data[from_resource_type]["relationships"][to_resource_type]
        relationships[(operation_type, field_name)] = {
            "schema": relationship_schema,
            "info": relationship_info,
        }

    def get_relationship_schema(
        self,
        from_resource_type: str,
        to_resource_type: str,
        operation_type: Literal["create", "update", "get"],
        field_name: str,
    ) -> Optional[TypeSchema]:
        self._init_resource_if_needed(from_resource_type)

        relationships = self._data[from_resource_type]["relationships"][to_resource_type]
        return relationships.get((operation_type, field_name), {}).get("schema")

    def add_resource(
        self,
        builder,
        resource_type: str,
        operation_type: Literal["create", "update", "get"],
        source_schema: Type[TypeSchema],
        data_schema: Type[TypeSchema],
        attributes_schema: Type[TypeSchema],
        field_schemas: dict[str, Type[TypeSchema]],
        relationships_info: dict[str, tuple[RelationshipInfo, Any]],
        model_validators: dict,
        meta_fields: Optional[list[str]] = None,
        schema_in: Optional[Type[TypeSchema]] = None,
    ):
        self._init_resource_if_needed(resource_type)
        if operation_type in self._data[resource_type]:
            return

        before_validators, after_validators = {}, {}
        for validator_name, validator in model_validators.items():
            if validator.decorator_info.mode == "before":
                before_validators[validator_name] = validator
            else:
                after_validators[validator_name] = validator

        self._source_schemas[resource_type] = source_schema
        self._data[resource_type][operation_type] = {
            "attrs_schema": attributes_schema,
            "field_schemas": field_schemas,
            "data_schema": data_schema,
            "meta_fields": meta_fields or [],
            "relationships_info": {
                relationship_name: info for relationship_name, (info, _) in relationships_info.items()
            },
            "relationships_pydantic_fields": {
                relationship_name: field for relationship_name, (_, field) in relationships_info.items()
            },
            "model_validators": (before_validators, after_validators),
        }

        if schema_in:
            self._data[resource_type][operation_type][self._schema_in_keys[operation_type]] = schema_in

    def get_source_schema(self, resource_type: str):
        try:
            return self._source_schemas[resource_type]
        except KeyError as ex:
            raise InternalServerError(detail=f"Not found source schema for resource type {resource_type!r}") from ex

    def get_source_relationship_pydantic_field(
        self,
        resource_type: str,
        operation_type: Literal["create", "update", "get"],
        field_name: str,
    ):
        return self._data[resource_type][operation_type]["relationships_pydantic_fields"][field_name]

    def get_data_schema(
        self,
        resource_type: str,
        operation_type: Literal["create", "update", "get"],
    ) -> Optional[TypeSchema]:
        return self._data[resource_type][operation_type]["data_schema"]

    def get_attrs_schema(
        self,
        resource_type: str,
        operation_type: Literal["create", "update", "get"],
    ) -> Optional[TypeSchema]:
        return self._data[resource_type][operation_type]["attrs_schema"]

    def get_field_schema(
        self,
        resource_type: str,
        operation_type: Literal["create", "update", "get"],
        field_name: str,
    ) -> Optional[TypeSchema]:
        return self._data[resource_type][operation_type]["field_schemas"].get(field_name)

    def get_schema_in(
        self,
        resource_type: str,
        operation_type: Literal["create", "update"],
    ) -> Type[TypeSchema]:
        try:
            return self._data[resource_type][operation_type][self._schema_in_keys[operation_type]]
        except KeyError as ex:
            raise InternalServerError(
                detail=f"Not found schema for operation {operation_type!r} with resource type {resource_type!r}",
            ) from ex

    def get_model_validators(
        self,
        resource_type: str,
        operation_type: Literal["create", "update", "get"],
    ) -> tuple[dict, dict]:
        return self._data[resource_type][operation_type]["model_validators"]

    def get_meta_fields(
        self,
        resource_type: str,
        operation_type: Literal["create", "update", "get"],
    ) -> list[str]:
        return self._data[resource_type][operation_type].get("meta_fields", [])

    def get_relationship_info(
        self,
        resource_type: str,
        operation_type: Literal["create", "update", "get"],
        field_name: str,
    ) -> Optional[RelationshipInfo]:
        return self._data[resource_type][operation_type]["relationships_info"].get(field_name)

    def get_relationships_info(
        self,
        resource_type: str,
        operation_type: Literal["create", "update", "get"],
    ) -> dict[str, RelationshipInfo]:
        return self._data[resource_type][operation_type]["relationships_info"]

    def get_jsonapi_object_schema(
        self,
        source_schema: Type[TypeSchema],
        resource_type: str,
    ) -> Optional[JSONAPIObjectSchemas]:
        return self._jsonapi_object_schemas.get((source_schema, resource_type))

    def add_jsonapi_object_schema(
        self,
        source_schema: Type[TypeSchema],
        resource_type: str,
        jsonapi_object_schema: JSONAPIObjectSchemas,
    ):
        self._jsonapi_object_schemas[(source_schema, resource_type)] = jsonapi_object_schema

    def has_resource(self, resource_type: str) -> bool:
        return resource_type in self._source_schemas

    def has_operation(
        self,
        resource_type: str,
        operation_type: Literal["create", "update", "get"],
    ) -> bool:
        return self.has_resource(resource_type) and operation_type in self._data[resource_type]


schemas_storage = SchemasStorage()
