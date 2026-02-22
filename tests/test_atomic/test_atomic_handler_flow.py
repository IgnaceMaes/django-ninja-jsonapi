from __future__ import annotations

from dataclasses import dataclass

import pytest
from django.http import HttpRequest

from django_ninja_jsonapi.atomic.atomic_handler import AtomicViewHandler, current_atomic_operation
from django_ninja_jsonapi.atomic.schemas import AtomicOperationRequest, OperationRelationshipSchema
from django_ninja_jsonapi.exceptions import HTTPException


class DummyDL:
    async def atomic_start(self, previous_dl=None):
        return None

    async def atomic_end(self, success=True, exception=None):
        return None


@dataclass
class FakeOperation:
    data: object
    response: dict | None = None
    error: Exception | None = None
    op_type: str = "update"
    ref: object | None = None

    async def get_data_layer(self):
        return DummyDL()

    def update_relationships_with_lid(self, local_ids):
        return None

    async def handle(self, dl):
        if self.error is not None:
            raise self.error
        return self.response


def _request() -> AtomicOperationRequest:
    return AtomicOperationRequest.model_validate(
        {
            "atomic:operations": [
                {
                    "op": "update",
                    "ref": {"type": "user", "id": "1"},
                    "data": {
                        "type": "user",
                        "id": "1",
                        "attributes": {},
                    },
                }
            ]
        }
    )


@pytest.mark.asyncio
async def test_atomic_handler_accepts_relationship_list_operation_data(monkeypatch):
    handler = AtomicViewHandler(request=HttpRequest(), operations_request=_request())
    operation = FakeOperation(
        data=[OperationRelationshipSchema(type="computer", id="10")],
        response={"data": {"type": "user", "id": "1"}},
    )

    async def fake_prepare_operations():
        return [operation]

    monkeypatch.setattr(handler, "prepare_operations", fake_prepare_operations)

    result = await handler.handle()

    assert result == {"atomic:results": [{"data": {"type": "user", "id": "1"}}]}
    assert not handler.local_ids_cache


@pytest.mark.asyncio
async def test_atomic_handler_resets_current_operation_context_on_error(monkeypatch):
    handler = AtomicViewHandler(request=HttpRequest(), operations_request=_request())
    operation = FakeOperation(
        data=[OperationRelationshipSchema(type="computer", id="10")],
        error=ValueError("broken"),
    )

    async def fake_prepare_operations():
        return [operation]

    monkeypatch.setattr(handler, "prepare_operations", fake_prepare_operations)

    with pytest.raises(HTTPException):
        await handler.handle()

    with pytest.raises(LookupError):
        current_atomic_operation.get()
