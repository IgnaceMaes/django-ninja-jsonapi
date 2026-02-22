"""Helper to create sqlalchemy filters according to filter querystring parameter"""

import logging
from collections import defaultdict
from typing import Any, Optional, Type, Union, get_args

from pydantic import BaseModel, ConfigDict, PydanticSchemaGenerationError, TypeAdapter

# noinspection PyProtectedMember
from pydantic._internal._typing_extra import is_none_type

# noinspection PyProtectedMember
from pydantic.fields import FieldInfo
from sqlalchemy import and_, false, not_, or_
from sqlalchemy.orm import aliased
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.orm.util import AliasedClass
from sqlalchemy.sql.elements import BinaryExpression

from django_ninja_jsonapi.common import search_custom_filter_sql, search_custom_sort_sql
from django_ninja_jsonapi.data_typing import TypeModel, TypeSchema
from django_ninja_jsonapi.exceptions import InvalidField, InvalidFilters, InvalidType
from django_ninja_jsonapi.exceptions.json_api import HTTPException, InternalServerError
from django_ninja_jsonapi.schema import (
    JSONAPISchemaIntrospectionError,
    get_model_field,
    get_relationship_fields_names,
    get_schema_from_field_annotation,
)
from django_ninja_jsonapi.types_metadata import CustomFilterSQL, CustomSortSQL

log = logging.getLogger(__name__)

cast_failed = object()


class RelationshipInfo(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    target_schema: Type[TypeSchema]
    model: Type[TypeModel]
    aliased_model: AliasedClass
    join_column: InstrumentedAttribute


class RelationshipInfoStorage:
    def __init__(self):
        self._data = defaultdict(dict)

    def has_info(self, resource_type: str, path: str) -> bool:
        return path in self._data[resource_type]

    def get_info(self, resource_type: str, path: str) -> RelationshipInfo:
        try:
            return self._data[resource_type][path]
        except KeyError as ex:
            raise InternalServerError(
                detail=(
                    f"Error of loading relationship info from storage for resource_type {resource_type!r}. "
                    f"Target relationship has path {path!r}."
                ),
                parameter="filter",
            ) from ex

    def set_info(self, resource_type: str, path: str, info: RelationshipInfo):
        self._data[resource_type][path] = info


relationships_info_storage = RelationshipInfoStorage()


def cast_value_with_schema(field_types: list[Type], value: Any) -> tuple[Any, list[str]]:
    errors: list[str] = []
    casted_value = cast_failed

    for field_type in field_types:
        try:
            # don't allow arbitrary types, we don't know their behaviour
            cast_type = TypeAdapter(field_type).validate_python
        except PydanticSchemaGenerationError:
            cast_type = field_type

        try:
            if isinstance(value, list):  # noqa: SIM108
                casted_value = [cast_type(item) for item in value]
            else:
                casted_value = cast_type(value)
        except (TypeError, ValueError) as ex:
            errors.append(f"{ex}")
        else:
            return casted_value, errors

    return casted_value, errors


def build_filter_expression(
    schema_field: FieldInfo,
    model_column: InstrumentedAttribute,
    operator: str,
    value: Any,
) -> BinaryExpression:
    """
    Builds sqlalchemy filter expression, like YourModel.some_field == value

    Custom sqlalchemy filtering logic can be created in a schemas field for any operator
    To implement a new filtering logic (override existing or create a new one)
    create a method inside a field following this pattern:  `_<your_op_name>_sql_filter_`

    :param schema_field: schemas field instance
    :param model_column: sqlalchemy column instance
    :param operator: your operator, for example: "eq", "in", "ilike_str_array", ...
    :param value: filtering value

    """
    fields = [schema_field]

    can_be_none = False
    for field in fields:
        if args := get_args(field.annotation):
            for arg in args:
                # None is probably only on the top level
                if is_none_type(arg):
                    can_be_none = True
                    break

    if value is None:
        if can_be_none:
            return getattr(model_column, operator)(value)

        raise InvalidFilters(detail=f"The field `{model_column.key}` can't be null.")

    casted_value, errors = cast_value_with_schema(
        field_types=[i.annotation for i in fields],
        value=value,
    )
    if casted_value is cast_failed:
        raise InvalidType(
            detail=f"Can't cast filter value `{value}` to arbitrary type.",
            errors=[HTTPException(status_code=InvalidType.status_code, detail=f"{err}") for err in errors],
        )

    if casted_value is None and not can_be_none:
        raise InvalidType(
            detail=", ".join(errors),
            pointer=schema_field.title,
        )

    return getattr(model_column, operator)(casted_value)


def is_filtering_terminal_node(filter_item: dict) -> bool:
    """
    If node shape is:

    {
        "name: ...,
        "op: ...,
        "val: ...,
    }
    """
    terminal_node_keys = {"name", "op", "val"}
    return set(filter_item.keys()) == terminal_node_keys


def is_relationship_filter(name: str) -> bool:
    return "." in name


def gather_relationship_paths(item: Union[dict, list[dict]]) -> set[str]:
    """
    Extracts relationship paths from query filter
    """
    names = set()

    if isinstance(item, list):
        for sub_item in item:
            names.update(gather_relationship_paths(sub_item))

    elif field_name := (item.get("name") or item.get("field")):
        if "." not in field_name:
            return set()

        return {".".join(field_name.split(".")[:-1])}

    else:
        for sub_item in item.values():
            names.update(gather_relationship_paths(sub_item))

    return names


def get_model_column(
    model: Type[TypeModel],
    schema: Type[TypeSchema],
    field_name: str,
) -> InstrumentedAttribute:
    try:
        model_field = get_model_field(schema, field_name)
    except JSONAPISchemaIntrospectionError as e:
        msg = f"{e}"
        raise InvalidFilters(msg) from e

    try:
        return getattr(model, model_field)
    except AttributeError as ex:
        msg = f"{model.__name__} has no attribute {model_field}"
        raise InvalidFilters(msg) from ex


def get_operator(model_column: InstrumentedAttribute, operator_name: str) -> str:
    """
    Get the function operator from his name

    :return callable: a callable to make operation on a column
    """
    operators = (
        f"__{operator_name}__",
        f"{operator_name}_",
        operator_name,
    )

    for op in operators:
        if hasattr(model_column, op):
            return op

    msg = f"Field {model_column.key!r} has no operator {operator_name!r}"
    raise InvalidFilters(msg)


def gather_relationships_info(
    model: Type[TypeModel],
    schema: Type[TypeSchema],
    entrypoint_resource_type: str,
    relationship_path: list[str],
    target_relationship_idx: int = 0,
    prev_aliased_model: Optional[Any] = None,
) -> dict[str, RelationshipInfo]:
    is_last_relationship = target_relationship_idx == len(relationship_path) - 1
    target_relationship_path = ".".join(
        relationship_path[: target_relationship_idx + 1],
    )
    target_relationship_name = relationship_path[target_relationship_idx]

    relationships_names = get_relationship_fields_names(schema)
    if target_relationship_name not in relationships_names:
        msg = f"There is no relationship {target_relationship_name!r} defined in schema {schema.__name__!r}"
        raise InvalidField(msg)

    target_schema = get_schema_from_field_annotation(schema.model_fields[target_relationship_name])
    target_model = getattr(model, target_relationship_name).property.mapper.class_

    if prev_aliased_model:
        join_column = get_model_column(
            model=prev_aliased_model,
            schema=schema,
            field_name=target_relationship_name,
        )
    else:
        join_column = get_model_column(
            model,
            schema,
            target_relationship_name,
        )

    aliased_model = aliased(target_model)
    relationships_info_storage.set_info(
        resource_type=entrypoint_resource_type,
        path=target_relationship_path,
        info=RelationshipInfo(
            target_schema=target_schema,
            model=target_model,
            aliased_model=aliased_model,
            join_column=join_column,
        ),
    )

    if not is_last_relationship:
        return gather_relationships_info(
            model=target_model,
            schema=target_schema,
            entrypoint_resource_type=entrypoint_resource_type,
            relationship_path=relationship_path,
            target_relationship_idx=target_relationship_idx + 1,
            prev_aliased_model=aliased_model,
        )


def gather_relationships(
    entrypoint_resource_type: str,
    entrypoint_model: Type[TypeModel],
    schema: Type[TypeSchema],
    relationship_paths: set[str],
) -> set[str]:
    for relationship_path in relationship_paths:
        if relationships_info_storage.has_info(entrypoint_resource_type, relationship_path):
            continue

        gather_relationships_info(
            model=entrypoint_model,
            schema=schema,
            entrypoint_resource_type=entrypoint_resource_type,
            relationship_path=relationship_path.split("."),
        )

    return relationship_paths


def prepare_relationships_info(
    model: Type[TypeModel],
    schema: Type[TypeSchema],
    resource_type: str,
    filter_info: list,
    sorting_info: list,
) -> set[str]:
    """
    Return set with request relationship paths in dot separated format.

    Gathers information about all relationships involved to request and save them
    data for skip extra computations for the next time.

    For the filter like this:
        filter_info = [
            {"field": "foo.bar.field_name", "op": "eq", "val": ""},
            {"field": "baz.field_name", "op": "eq", "val": ""},
        ]

    It returns:
        ("foo.bar", "baz")
    """
    relationship_paths = gather_relationship_paths(filter_info)
    relationship_paths.update(gather_relationship_paths(sorting_info))
    return gather_relationships(
        entrypoint_resource_type=resource_type,
        entrypoint_model=model,
        schema=schema,
        relationship_paths=relationship_paths,
    )


def build_terminal_node_filter_expressions(
    filter_item: dict,
    target_schema: Type[TypeSchema],
    target_model: Type[TypeModel],
    entrypoint_resource_type: str,
):
    name: str = filter_item["name"]
    if is_relationship_filter(name):
        *relationship_path, field_name = name.split(".")
        relationship_info: RelationshipInfo = relationships_info_storage.get_info(
            resource_type=entrypoint_resource_type,
            path=".".join(relationship_path),
        )
        model_column = get_model_column(
            model=relationship_info.aliased_model,
            schema=relationship_info.target_schema,
            field_name=field_name,
        )
        target_schema = relationship_info.target_schema
    else:
        field_name = name
        model_column = get_model_column(
            model=target_model,
            schema=target_schema,
            field_name=field_name,
        )

    schema_field = target_schema.model_fields[field_name]

    filter_operator = filter_item["op"]
    custom_filter_sql: Optional[CustomFilterSQL] = None
    for filter_sql in search_custom_filter_sql.iterate(field=schema_field):
        if filter_sql.op == filter_operator:
            custom_filter_sql = filter_sql
            break

    if custom_filter_sql is None:
        return build_filter_expression(
            schema_field=schema_field,
            model_column=model_column,
            operator=get_operator(
                model_column=model_column,
                operator_name=filter_operator,
            ),
            value=filter_item["val"],
        )

    return custom_filter_sql.get_expression(
        schema_field=schema_field,
        model_column=model_column,
        value=filter_item["val"],
        operator=filter_operator,
    )


def build_filter_expressions(
    filter_item: dict,
    target_schema: Type[TypeSchema],
    target_model: Type[TypeModel],
    entrypoint_resource_type: str,
) -> BinaryExpression:
    """
    Return sqla expressions.

    Builds sqlalchemy expression which can be use
    in where condition: query(Model).where(build_filter_expressions(...))
    """
    if is_filtering_terminal_node(filter_item):
        return build_terminal_node_filter_expressions(
            filter_item=filter_item,
            target_schema=target_schema,
            target_model=target_model,
            entrypoint_resource_type=entrypoint_resource_type,
        )

    if not isinstance(filter_item, dict):
        log.warning("Could not build filtering expressions %s", locals())
        # dirty. refactor.
        return not_(false())

    sqla_logic_operators = {
        "or": or_,
        "and": and_,
        "not": not_,
    }

    if len(logic_operators := set(filter_item.keys())) > 1:
        msg = (
            f"In each logic node expected one of operators: {set(sqla_logic_operators.keys())} "
            f"but got {len(logic_operators)}: {logic_operators}"
        )
        raise InvalidFilters(msg)

    if (logic_operator := logic_operators.pop()) not in set(sqla_logic_operators.keys()):
        msg = f"Not found logic operator {logic_operator} expected one of {set(sqla_logic_operators.keys())}"
        raise InvalidFilters(msg)

    op = sqla_logic_operators[logic_operator]

    if logic_operator == "not":
        return op(
            build_filter_expressions(
                filter_item=filter_item[logic_operator],
                target_schema=target_schema,
                target_model=target_model,
                entrypoint_resource_type=entrypoint_resource_type,
            ),
        )

    return op(
        *(
            build_filter_expressions(
                filter_item=filter_sub_item,
                target_schema=target_schema,
                target_model=target_model,
                entrypoint_resource_type=entrypoint_resource_type,
            )
            for filter_sub_item in filter_item[logic_operator]
        ),
    )


def build_sort_expressions(
    sort_items: list[dict],
    target_schema: Type[TypeSchema],
    target_model: Type[TypeModel],
    entrypoint_resource_type: str,
):
    expressions = []
    for item in sort_items:
        schema = target_schema
        model, field_name = target_model, item["field"]

        if relationship_path := item.get("rel_path"):
            field_name = item["field"].split(".")[-1]
            info = relationships_info_storage.get_info(
                resource_type=entrypoint_resource_type,
                path=relationship_path,
            )
            model = info.aliased_model
            schema = info.target_schema

        schema_field = schema.model_fields[field_name]
        custom_sort_sql: Optional[CustomSortSQL] = search_custom_sort_sql.first(field=schema_field)

        join_column = getattr(model, field_name)
        if custom_sort_sql is not None:
            join_column = custom_sort_sql.get_expression(schema_field, join_column)

        expressions.append(getattr(join_column, item["order"])())

    return expressions
