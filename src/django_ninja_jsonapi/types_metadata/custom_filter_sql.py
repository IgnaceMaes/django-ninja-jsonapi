import contextlib
import logging
from dataclasses import dataclass
from typing import Any, Generic, TypeVar, Union, cast

import orjson as json

# noinspection PyProtectedMember
from pydantic.fields import FieldInfo
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB as JSONB_SQLA
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy.sql.expression import BinaryExpression, BooleanClauseList

from django_ninja_jsonapi.exceptions import InvalidFilters

log = logging.getLogger(__name__)

ColumnType = TypeVar("ColumnType")
ExpressionType = TypeVar("ExpressionType")


@dataclass(frozen=True)
class CustomFilterSQL(Generic[ColumnType, ExpressionType]):
    op: str

    def get_expression(
        self,
        schema_field: FieldInfo,
        model_column: ColumnType,
        value: str,
        operator: str,
    ) -> ExpressionType:
        raise NotImplementedError


class CustomFilterSQLA(CustomFilterSQL[InstrumentedAttribute, Union[BinaryExpression, BooleanClauseList]]):
    """Base class for custom SQLAlchemy filters"""


def _get_pg_jsonb_contains_expression(
    model_column: InstrumentedAttribute,
    value: Any,
) -> BinaryExpression:
    with contextlib.suppress(ValueError):
        value = json.loads(value)

    return model_column.cast(JSONB_SQLA).op("@>")(value)


def _get_sqlite_json_contains_expression(
    model_column: InstrumentedAttribute,
    value: Any,
) -> BinaryExpression:
    with contextlib.suppress(ValueError):
        value = json.loads(value)

    return model_column.ilike(value)


def _get_pg_jsonb_ilike_expression(
    model_column: InstrumentedAttribute,
    value: list,
    operator: str,
) -> BinaryExpression:
    try:
        target_field, regex = value
    except ValueError as ex:
        msg = f'The "value" field has to be list of two values for op `{operator}`'
        raise InvalidFilters(msg) from ex

    if isinstance(regex, (list, dict)):
        return model_column[target_field].cast(JSONB_SQLA).op("@>")(regex)
    elif isinstance(regex, bool):
        regex = f"{regex}".lower()
    else:
        regex = f"{regex}"

    return model_column.op("->>")(target_field).ilike(regex)


def _get_sqlite_json_ilike_expression(
    model_column: InstrumentedAttribute,
    value: list,
    operator: str,
) -> BinaryExpression:
    try:
        target_field, regex = value
    except ValueError as ex:
        msg = f'The "value" field has to be list of two values for op `{operator}`'
        raise InvalidFilters(msg) from ex

    if isinstance(regex, (list, dict)):
        regex = json.dumps(regex).decode()
    elif isinstance(regex, bool):
        return model_column.op("->>")(target_field).is_(regex)
    else:
        regex = f"{regex}"

    return model_column.op("->>")(target_field).ilike(regex)


class LowerEqualsFilterSQL(CustomFilterSQLA):
    def get_expression(
        self,
        schema_field: FieldInfo,
        model_column: InstrumentedAttribute,
        value: str,
        operator: str,
    ) -> BinaryExpression:
        return cast(
            BinaryExpression,
            func.lower(model_column) == func.lower(value),
        )


class PGJSONContainsFilterSQL(CustomFilterSQLA):
    def get_expression(
        self,
        schema_field: FieldInfo,
        model_column: InstrumentedAttribute,
        value: Any,
        operator: str,
    ) -> BinaryExpression:
        return _get_pg_jsonb_contains_expression(model_column, value)


class PGJSONBContainsFilterSQL(CustomFilterSQLA):
    def get_expression(
        self,
        schema_field: FieldInfo,
        model_column: InstrumentedAttribute,
        value: Any,
        operator: str,
    ) -> BinaryExpression:
        return _get_pg_jsonb_contains_expression(model_column, value)


class PGJSONIlikeFilterSQL(CustomFilterSQLA):
    def get_expression(
        self,
        schema_field: FieldInfo,
        model_column: InstrumentedAttribute,
        value: list[str],
        operator: str,
    ) -> BinaryExpression:
        return _get_pg_jsonb_ilike_expression(model_column, value, operator)


class PGJSONBIlikeFilterSQL(CustomFilterSQLA):
    def get_expression(
        self,
        schema_field: FieldInfo,
        model_column: InstrumentedAttribute,
        value: list[str],
        operator: str,
    ) -> BinaryExpression:
        return _get_pg_jsonb_ilike_expression(model_column, value, operator)


class SQLiteJSONContainsFilterSQL(CustomFilterSQLA):
    def get_expression(
        self,
        schema_field: FieldInfo,
        model_column: InstrumentedAttribute,
        value: Any,
        operator: str,
    ) -> BinaryExpression:
        return _get_sqlite_json_contains_expression(model_column, value)


class SQLiteJSONIlikeFilterSQL(CustomFilterSQLA):
    def get_expression(
        self,
        schema_field: FieldInfo,
        model_column: InstrumentedAttribute,
        value: list[str],
        operator: str,
    ) -> BinaryExpression:
        return _get_sqlite_json_ilike_expression(model_column, value, operator)


sql_filter_lower_equals = LowerEqualsFilterSQL(op="lower_equals")
sql_filter_pg_json_contains = PGJSONContainsFilterSQL(op="pg_json_contains")
sql_filter_pg_jsonb_contains = PGJSONBContainsFilterSQL(op="pg_jsonb_contains")
sql_filter_pg_json_ilike = PGJSONIlikeFilterSQL(op="pg_json_ilike")
sql_filter_pg_jsonb_ilike = PGJSONBIlikeFilterSQL(op="pg_jsonb_ilike")
sql_filter_sqlite_json_contains = SQLiteJSONContainsFilterSQL(op="sqlite_json_contains")
sql_filter_sqlite_json_ilike = SQLiteJSONIlikeFilterSQL(op="sqlite_json_ilike")
