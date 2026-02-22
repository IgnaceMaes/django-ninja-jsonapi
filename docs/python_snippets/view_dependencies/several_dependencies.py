from pydantic import BaseModel

from django_ninja_jsonapi import ViewBaseGeneric
from django_ninja_jsonapi.views import Operation, OperationConfig


class CommonDependency(BaseModel):
    key_1: int = 1


class GetDependency(BaseModel):
    key_2: int = 2


def common_handler(view, dto: CommonDependency) -> dict:
    return {"key_1": dto.key_1}


def get_handler(view, dto: GetDependency) -> dict:
    return {"key_2": dto.key_2}


class CustomerView(ViewBaseGeneric):
    operation_dependencies = {
        Operation.ALL: OperationConfig(
            dependencies=CommonDependency,
            prepare_data_layer_kwargs=common_handler,
        ),
        Operation.GET: OperationConfig(
            dependencies=GetDependency,
            prepare_data_layer_kwargs=get_handler,
        ),
    }
