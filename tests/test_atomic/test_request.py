import pytest
from pydantic import ValidationError

from django_ninja_jsonapi.atomic.schemas import AtomicOperationRequest


@pytest.mark.parametrize(
    "operation_request",
    [
        {
            "atomic:operations": [
                {
                    "op": "add",
                    "href": "/articles",
                    "data": {
                        "type": "articles",
                        "attributes": {
                            "title": "JSON API paints my bikeshed!",
                        },
                    },
                },
            ],
        },
        {
            "atomic:operations": [
                {
                    "op": "update",
                    "data": {
                        "type": "articles",
                        "id": "13",
                        "attributes": {"title": "To TDD or Not"},
                    },
                },
            ],
        },
        {
            "atomic:operations": [
                {
                    "op": "remove",
                    "ref": {
                        "type": "articles",
                        "id": "13",
                    },
                },
            ],
        },
    ],
)
def test_atomic_operation_request_valid_payloads(operation_request: dict):
    validated = AtomicOperationRequest.model_validate(operation_request)
    assert validated.model_dump(exclude_unset=True, by_alias=True) == operation_request


def test_atomic_operation_request_invalid_operation_name():
    operation_request = {
        "atomic:operations": [
            {
                "op": "not-supported",
                "href": "/any",
                "data": {
                    "type": "any",
                    "attributes": {
                        "name": "value",
                    },
                },
            },
        ],
    }

    with pytest.raises(ValidationError) as exc_info:
        AtomicOperationRequest.model_validate(operation_request)

    assert "Input should be" in exc_info.value.errors()[0]["msg"]


def test_atomic_remove_requires_ref():
    operation_request = {
        "atomic:operations": [
            {
                "op": "remove",
                "data": {
                    "type": "articles",
                },
            },
        ],
    }

    with pytest.raises(ValidationError) as exc_info:
        AtomicOperationRequest.model_validate(operation_request)

    assert "ref should be present" in exc_info.value.errors()[0]["msg"]
