import json

import pytest
from django.test import RequestFactory
from pydantic import BaseModel

from django_ninja_jsonapi.decorators import jsonapi_resource
from django_ninja_jsonapi.renderers import (
    REQUEST_JSONAPI_CONFIG_ATTR,
    JSONAPIRelationshipConfig,
    JSONAPIRenderer,
    JSONAPIResourceConfig,
)
from django_ninja_jsonapi.response_helpers import jsonapi_include, jsonapi_links, jsonapi_meta


def _render_payload(request, data):
    payload = JSONAPIRenderer().render(request, data, response_status=200)
    if isinstance(payload, bytes):
        return json.loads(payload.decode())

    return json.loads(payload)


def test_renderer_passthrough_without_metadata():
    request = RequestFactory().get("/articles/1/")

    result = _render_payload(request, {"hello": "world"})

    assert result == {"hello": "world"}


def test_renderer_wraps_detail_payload_with_jsonapi_document():
    request = RequestFactory().get("/articles/1/")
    setattr(request, REQUEST_JSONAPI_CONFIG_ATTR, JSONAPIResourceConfig(resource_type="articles"))

    result = _render_payload(request, {"id": 1, "title": "Hello"})

    assert result["data"]["id"] == "1"
    assert result["data"]["type"] == "articles"
    assert result["data"]["attributes"] == {"title": "Hello"}
    assert result["links"]["self"] == "http://testserver/articles/1/"
    assert result["jsonapi"] == {"version": "1.0"}


def test_renderer_wraps_list_payload_with_item_links():
    request = RequestFactory().get("/articles/")
    setattr(request, REQUEST_JSONAPI_CONFIG_ATTR, JSONAPIResourceConfig(resource_type="articles"))

    result = _render_payload(request, [{"id": 1, "title": "Hello"}, {"id": 2, "title": "World"}])

    assert len(result["data"]) == 2
    assert result["data"][0]["links"]["self"] == "http://testserver/articles/1/"
    assert result["data"][1]["links"]["self"] == "http://testserver/articles/2/"


def test_renderer_relationships_with_included_meta_and_links_helpers():
    request = RequestFactory().get("/articles/1/?include=author")
    setattr(
        request,
        REQUEST_JSONAPI_CONFIG_ATTR,
        JSONAPIResourceConfig(
            resource_type="articles",
            relationships={"author": JSONAPIRelationshipConfig(resource_type="people")},
        ),
    )

    jsonapi_include(request, {"id": 9, "name": "Alice"}, resource_type="people")
    jsonapi_meta(request, count=1)
    jsonapi_links(request, related="http://testserver/articles/1/author/")

    result = _render_payload(request, {"id": 1, "title": "Hello", "author": {"id": 9}})

    assert result["data"]["relationships"]["author"]["data"] == {"id": "9", "type": "people"}
    assert result["data"]["relationships"]["author"]["links"]["self"] == (
        "http://testserver/articles/1/relationships/author/"
    )
    assert result["included"] == [
        {
            "id": "9",
            "type": "people",
            "attributes": {"name": "Alice"},
            "links": {"self": "http://testserver/people/9/"},
        }
    ]
    assert result["meta"] == {"count": 1}
    assert result["links"]["related"] == "http://testserver/articles/1/author/"


def test_renderer_skips_rewrapping_for_jsonapi_documents():
    request = RequestFactory().get("/articles/1/")
    setattr(request, REQUEST_JSONAPI_CONFIG_ATTR, JSONAPIResourceConfig(resource_type="articles"))
    payload = {
        "data": {"type": "articles", "id": "1", "attributes": {"title": "Hello"}},
        "jsonapi": {"version": "1.0"},
    }

    result = _render_payload(request, payload)

    assert result == payload


def test_jsonapi_resource_decorator_sets_request_metadata_for_sync_functions():
    request = RequestFactory().get("/articles/1/")

    @jsonapi_resource("articles")
    def endpoint(request, article_id: int):
        return {"id": article_id, "title": "Hello"}

    _ = endpoint(request, 1)

    config = getattr(request, REQUEST_JSONAPI_CONFIG_ATTR)
    assert config.resource_type == "articles"


@pytest.mark.asyncio
async def test_jsonapi_resource_decorator_sets_request_metadata_for_async_functions():
    request = RequestFactory().get("/articles/1/")

    @jsonapi_resource(
        "articles",
        relationships={"author": {"resource_type": "people", "many": False}},
    )
    async def endpoint(request, article_id: int):
        return {"id": article_id, "title": "Hello", "author": {"id": 9}}

    _ = await endpoint(request, 1)

    config = getattr(request, REQUEST_JSONAPI_CONFIG_ATTR)
    assert config.resource_type == "articles"
    assert config.relationships["author"].resource_type == "people"


# ---------------------------------------------------------------------------
# Auto-serialization: Pydantic models
# ---------------------------------------------------------------------------


class ArticlePydantic(BaseModel):
    id: int
    title: str


def test_renderer_accepts_pydantic_model_instance():
    request = RequestFactory().get("/articles/1/")
    setattr(request, REQUEST_JSONAPI_CONFIG_ATTR, JSONAPIResourceConfig(resource_type="articles"))

    article = ArticlePydantic(id=1, title="From Pydantic")
    result = _render_payload(request, article)

    assert result["data"]["id"] == "1"
    assert result["data"]["type"] == "articles"
    assert result["data"]["attributes"] == {"title": "From Pydantic"}


def test_renderer_accepts_list_of_pydantic_models():
    request = RequestFactory().get("/articles/")
    setattr(request, REQUEST_JSONAPI_CONFIG_ATTR, JSONAPIResourceConfig(resource_type="articles"))

    articles = [
        ArticlePydantic(id=1, title="First"),
        ArticlePydantic(id=2, title="Second"),
    ]
    result = _render_payload(request, articles)

    assert len(result["data"]) == 2
    assert result["data"][0]["attributes"]["title"] == "First"
    assert result["data"][1]["attributes"]["title"] == "Second"


def test_renderer_rejects_unsupported_types():
    request = RequestFactory().get("/articles/1/")
    setattr(request, REQUEST_JSONAPI_CONFIG_ATTR, JSONAPIResourceConfig(resource_type="articles"))

    with pytest.raises(TypeError, match="JSON:API renderer expects"):
        _render_payload(request, "not a dict or model")