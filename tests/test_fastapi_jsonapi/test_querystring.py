import pytest
from django.test import RequestFactory, override_settings
from pydantic import BaseModel

from django_ninja_jsonapi.exceptions import BadRequest, InvalidField, InvalidFilters, InvalidInclude, InvalidType
from django_ninja_jsonapi.querystring import QueryStringManager
from django_ninja_jsonapi.storages.schemas_storage import schemas_storage


class UserAttrsSchema(BaseModel):
    name: str
    email: str


def test_extract_item_key_success_and_parse_error():
    assert QueryStringManager.extract_item_key("fields[user]") == "user"

    with pytest.raises(BadRequest) as exc_info:
        QueryStringManager.extract_item_key("fields[user")

    assert exc_info.value.status_code == 400
    assert exc_info.value.as_dict["source"] == {"parameter": "fields[user"}


def test_filters_invalid_json_raises_invalid_filters():
    request = RequestFactory().get("/api/users", {"filter": "not-json"})

    with pytest.raises(InvalidFilters):
        _ = QueryStringManager(request).filters


def test_filters_non_list_raises_invalid_filters():
    request = RequestFactory().get("/api/users", {"filter": '{"name":"john"}'})

    with pytest.raises(InvalidFilters) as exc_info:
        _ = QueryStringManager(request).filters

    assert "expected list of conditions" in exc_info.value.as_dict["detail"]


def test_fields_unknown_resource_type_raises_invalid_type():
    request = RequestFactory().get("/api/users", {"fields[user]": "name"})

    with pytest.raises(InvalidType):
        _ = QueryStringManager(request).fields


def test_fields_unknown_attribute_raises_invalid_field(monkeypatch):
    monkeypatch.setattr(schemas_storage, "has_resource", lambda resource_type: True)
    monkeypatch.setattr(schemas_storage, "get_attrs_schema", lambda resource_type, operation_type: UserAttrsSchema)

    request = RequestFactory().get("/api/users", {"fields[user]": "missing_field"})

    with pytest.raises(InvalidField):
        _ = QueryStringManager(request).fields


@override_settings(NINJA_JSONAPI={"MAX_INCLUDE_DEPTH": 1, "MAX_PAGE_SIZE": 100, "ALLOW_DISABLE_PAGINATION": True})
def test_include_depth_limit_raises_invalid_include():
    request = RequestFactory().get("/api/users", {"include": "posts.author"})

    with pytest.raises(InvalidInclude):
        _ = QueryStringManager(request).include


@override_settings(NINJA_JSONAPI={"ALLOW_DISABLE_PAGINATION": False, "MAX_PAGE_SIZE": 100, "MAX_INCLUDE_DEPTH": 3})
def test_disable_pagination_not_allowed_raises_bad_request():
    request = RequestFactory().get("/api/users", {"page[size]": "0"})

    with pytest.raises(BadRequest):
        _ = QueryStringManager(request).pagination
