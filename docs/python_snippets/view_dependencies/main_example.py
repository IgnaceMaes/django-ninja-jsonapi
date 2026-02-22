from pydantic import BaseModel

from django_ninja_jsonapi import ViewBaseGeneric
from django_ninja_jsonapi.views import Operation, OperationConfig


class TenantDependency(BaseModel):
    tenant_id: str = "tenant-1"


def all_handler(view, dto: TenantDependency) -> dict:
    return {"tenant_id": dto.tenant_id}


class CustomerView(ViewBaseGeneric):
    operation_dependencies = {
        Operation.ALL: OperationConfig(
            dependencies=TenantDependency,
            prepare_data_layer_kwargs=all_handler,
        ),
    }
