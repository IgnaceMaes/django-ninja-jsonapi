import json

from django.test import RequestFactory
from pydantic import BaseModel, ValidationError

from django_ninja_jsonapi.exceptions import BadRequest
from django_ninja_jsonapi.exceptions.handlers import base_exception_handler, pydantic_validation_exception_handler
from django_ninja_jsonapi.renderers import JSONAPI_MEDIA_TYPE


def test_base_exception_handler_returns_jsonapi_error_shape():
    request = RequestFactory().get("/api/test")
    response = base_exception_handler(request, BadRequest(detail="invalid input", parameter="filter"))

    assert response.status_code == 400

    payload = json.loads(response.content.decode())
    assert "errors" in payload
    assert payload["errors"][0]["detail"] == "invalid input"
    assert payload["errors"][0]["source"] == {"parameter": "filter"}
    assert response["Content-Type"].startswith(JSONAPI_MEDIA_TYPE)


def test_pydantic_validation_exception_handler_returns_jsonapi_errors():
    request = RequestFactory().post("/api/test")

    class StrictModel(BaseModel):
        name: str
        age: int

    try:
        StrictModel(name=123, age="not-a-number")
    except ValidationError as exc:
        response = pydantic_validation_exception_handler(request, exc)

    assert response.status_code == 422
    payload = json.loads(response.content.decode())
    assert "errors" in payload
    assert len(payload["errors"]) >= 1
    for error in payload["errors"]:
        assert error["status"] == "422"
        assert error["title"] == "Validation Error"
        assert "detail" in error
        assert "source" in error
        assert "pointer" in error["source"]
    assert response["Content-Type"].startswith(JSONAPI_MEDIA_TYPE)


def test_pydantic_validation_error_pointer_includes_field_location():
    request = RequestFactory().post("/api/test")

    class StrictModel(BaseModel):
        email: str

    try:
        StrictModel()  # missing required field
    except ValidationError as exc:
        response = pydantic_validation_exception_handler(request, exc)

    payload = json.loads(response.content.decode())
    pointers = [e["source"]["pointer"] for e in payload["errors"]]
    assert any("email" in p for p in pointers)
