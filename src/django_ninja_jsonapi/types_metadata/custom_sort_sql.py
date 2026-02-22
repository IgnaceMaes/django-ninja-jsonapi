from dataclasses import dataclass
from typing import Generic, TypeVar, Union

# noinspection PyProtectedMember
from pydantic.fields import FieldInfo
from sqlalchemy import func
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy.sql.expression import BinaryExpression, BooleanClauseList

ColumnType = TypeVar("ColumnType")
ExpressionType = TypeVar("ExpressionType")


@dataclass(frozen=True)
class CustomSortSQL(Generic[ColumnType, ExpressionType]):
    def get_expression(
        self,
        schema_field: FieldInfo,
        model_column: ColumnType,
    ) -> ExpressionType:
        raise NotImplementedError


class CustomSortSQLA(CustomSortSQL[InstrumentedAttribute, Union[BinaryExpression, BooleanClauseList]]):
    """Base class for custom SQLAlchemy sorts"""


class RegisterFreeStringSortSQL(CustomSortSQLA):
    def get_expression(
        self,
        schema_field: FieldInfo,
        model_column: InstrumentedAttribute,
    ) -> BinaryExpression:
        return func.lower(model_column)


sql_register_free_sort = RegisterFreeStringSortSQL()
