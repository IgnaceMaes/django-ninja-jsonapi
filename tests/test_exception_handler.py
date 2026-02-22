import json

from django.test import RequestFactory

from django_ninja_jsonapi.exceptions import BadRequest
from django_ninja_jsonapi.exceptions.handlers import base_exception_handler
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
