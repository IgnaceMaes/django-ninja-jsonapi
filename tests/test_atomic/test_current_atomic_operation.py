from contextvars import Token
from types import SimpleNamespace

import pytest

from django_ninja_jsonapi.atomic.atomic_handler import catch_exc_on_operation_handle, current_atomic_operation
from django_ninja_jsonapi.atomic.schemas import OperationItemInSchema
from django_ninja_jsonapi.exceptions import HTTPException


@pytest.mark.asyncio
async def test_catch_exc_on_operation_handle_wraps_value_error_to_http_exception():
    operation = SimpleNamespace(
        op_type="add",
        ref=None,
        data=OperationItemInSchema(type="user", attributes={"name": "x"}),
    )

    @catch_exc_on_operation_handle
    async def fn(*, operation):
        raise ValueError("broken")

    with pytest.raises(HTTPException) as exc_info:
        await fn(operation=operation)

    assert exc_info.value.status_code == 422
    assert "Validation error on operation add" in exc_info.value.as_dict["detail"]["message"]


def test_current_atomic_operation_context_var_roundtrip():
    op = object()

    token: Token = current_atomic_operation.set(op)
    try:
        assert current_atomic_operation.get() is op
    finally:
        current_atomic_operation.reset(token)

    with pytest.raises(LookupError):
        current_atomic_operation.get()
