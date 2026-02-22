import pytest

from django_ninja_jsonapi.atomic.schemas import AtomicResultResponse


@pytest.mark.parametrize(
    "operation_response",
    [
        {
            "atomic:results": [
                {
                    "data": {
                        "type": "articles",
                        "id": "13",
                        "attributes": {
                            "title": "JSON API paints my bikeshed!",
                        },
                    },
                },
            ],
        },
        {
            "atomic:results": [
                {
                    "data": {
                        "type": "users",
                        "id": "user-1",
                        "attributes": {"name": "dgeb"},
                    },
                },
                {
                    "data": {
                        "type": "articles",
                        "id": "article-1",
                        "attributes": {
                            "title": "JSON API paints my bikeshed!",
                        },
                    },
                },
            ],
        },
    ],
)
def test_atomic_result_response_valid_payloads(operation_response: dict):
    validated = AtomicResultResponse.model_validate(operation_response)
    assert validated.model_dump(exclude_unset=True, by_alias=True) == operation_response
