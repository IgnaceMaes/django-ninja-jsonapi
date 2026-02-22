import pytest
from django.test import RequestFactory

from django_ninja_jsonapi.api.endpoint_builder import EndpointsBuilder
from django_ninja_jsonapi.exceptions import BadRequest


def test_parse_json_body_raises_bad_request_for_malformed_json():
    request = RequestFactory().generic(
        method="POST",
        path="/api/users",
        data=b'{"invalid": ',
        content_type="application/json",
    )

    with pytest.raises(BadRequest) as exc_info:
        EndpointsBuilder._parse_json_body(request)

    assert exc_info.value.as_dict["detail"] == "Malformed JSON request body"
    assert exc_info.value.as_dict["source"] == {"parameter": "body"}
