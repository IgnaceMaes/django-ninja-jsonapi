"""Tests for NinjaJsonAPI transparent JSON:API layer."""

from typing import ClassVar

from django.test import RequestFactory
from ninja.testing import TestClient
from pydantic import BaseModel, ConfigDict

from django_ninja_jsonapi.meta import JsonApiMeta
from django_ninja_jsonapi.transparent import (
    NinjaJsonAPI,
    get_rel_id,
    get_rel_ids,
)

# ---------------------------------------------------------------------------
# Test schemas
# ---------------------------------------------------------------------------


class TagSchema(BaseModel):
    id: int
    name: str
    jsonapi_meta: ClassVar[JsonApiMeta] = JsonApiMeta(resource_type="tags")


class UserSchema(BaseModel):
    id: int
    name: str
    jsonapi_meta: ClassVar[JsonApiMeta] = JsonApiMeta(resource_type="people")


class ArticleSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    body: str
    author: UserSchema | None = None
    tags: list[TagSchema] = []

    jsonapi_meta: ClassVar[JsonApiMeta] = JsonApiMeta(resource_type="articles")


class ArticleCreateSchema(BaseModel):
    title: str
    body: str

    jsonapi_meta: ClassVar[JsonApiMeta] = JsonApiMeta(resource_type="articles")


class ArticleUpdateSchema(BaseModel):
    title: str | None = None
    body: str | None = None

    jsonapi_meta: ClassVar[JsonApiMeta] = JsonApiMeta(resource_type="articles")


class SimpleSchema(BaseModel):
    id: int
    name: str

    jsonapi_meta: ClassVar[JsonApiMeta] = JsonApiMeta(resource_type="simples")


class SimpleCreateSchema(BaseModel):
    name: str

    jsonapi_meta: ClassVar[JsonApiMeta] = JsonApiMeta(resource_type="simples")


# ---------------------------------------------------------------------------
# get_rel_id / get_rel_ids (request-level helpers)
# ---------------------------------------------------------------------------


class TestGetRelId:
    def test_returns_none_when_no_relationships(self):
        request = RequestFactory().post("/test/")
        assert get_rel_id(request, "author") is None

    def test_returns_none_for_unknown_relationship(self):
        request = RequestFactory().post("/test/")
        # Simulate stashed relationships with no matching field
        from pydantic import BaseModel as BM

        class FakeRels(BM):
            pass

        from django_ninja_jsonapi.transparent import REQUEST_JSONAPI_BODY_RELATIONSHIPS_ATTR

        setattr(request, REQUEST_JSONAPI_BODY_RELATIONSHIPS_ATTR, FakeRels())
        assert get_rel_id(request, "nonexistent") is None


class TestGetRelIds:
    def test_returns_empty_when_no_relationships(self):
        request = RequestFactory().post("/test/")
        assert get_rel_ids(request, "tags") == []


# ---------------------------------------------------------------------------
# NinjaJsonAPI — integration tests
# ---------------------------------------------------------------------------


class TestNinjaJsonAPIGet:
    def test_get_detail_returns_jsonapi_document(self):
        api = NinjaJsonAPI(urls_namespace="test-get-detail")

        @api.get("/items/{item_id}", response=SimpleSchema)
        def get_item(request, item_id: int):
            return {"id": item_id, "name": "Test Item"}

        client = TestClient(api)
        response = client.get("/items/1")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert data["data"]["id"] == "1"
        assert data["data"]["type"] == "simples"
        assert data["data"]["attributes"]["name"] == "Test Item"

    def test_get_list_returns_jsonapi_collection(self):
        api = NinjaJsonAPI(urls_namespace="test-get-list")

        @api.get("/items", response=list[SimpleSchema])
        def list_items(request):
            return [{"id": 1, "name": "One"}, {"id": 2, "name": "Two"}]

        client = TestClient(api)
        response = client.get("/items")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]) == 2
        assert data["data"][0]["type"] == "simples"
        assert data["data"][1]["attributes"]["name"] == "Two"

    def test_get_with_relationships(self):
        api = NinjaJsonAPI(urls_namespace="test-get-rels")

        @api.get("/articles/{id}", response=ArticleSchema)
        def get_article(request, id: int):
            return {
                "id": id,
                "title": "Hello",
                "body": "World",
                "author": {"id": 5, "name": "Alice"},
                "tags": [{"id": 1, "name": "python"}],
            }

        client = TestClient(api)
        response = client.get("/articles/1")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["type"] == "articles"
        assert data["data"]["relationships"]["author"]["data"]["id"] == "5"
        assert data["data"]["relationships"]["author"]["data"]["type"] == "people"
        assert data["data"]["relationships"]["tags"]["data"][0]["id"] == "1"
        assert data["data"]["relationships"]["tags"]["data"][0]["type"] == "tags"


class TestNinjaJsonAPIPost:
    def test_post_unwraps_body(self):
        api = NinjaJsonAPI(urls_namespace="test-post-unwrap")

        captured = {}

        @api.post("/items", response={201: SimpleSchema})
        def create_item(request, body: SimpleCreateSchema):
            captured["body_type"] = type(body).__name__
            captured["name"] = body.name
            return 201, {"id": 1, "name": body.name}

        client = TestClient(api)
        response = client.post(
            "/items",
            json={
                "data": {
                    "type": "simples",
                    "attributes": {"name": "New Item"},
                }
            },
            content_type="application/vnd.api+json",
        )

        assert response.status_code == 201
        assert captured["body_type"] == "SimpleCreateSchema"
        assert captured["name"] == "New Item"
        data = response.json()
        assert data["data"]["type"] == "simples"

    def test_post_with_relationships_stashed_on_request(self):
        api = NinjaJsonAPI(urls_namespace="test-post-rels")

        captured = {}

        class ItemCreateSchema(BaseModel):
            name: str
            jsonapi_meta: ClassVar[JsonApiMeta] = JsonApiMeta(resource_type="items")

        class ItemSchema(BaseModel):
            id: int
            name: str
            author: UserSchema | None = None
            jsonapi_meta: ClassVar[JsonApiMeta] = JsonApiMeta(resource_type="items")

        @api.post("/items", response={201: ItemSchema})
        def create_item(request, body: ItemCreateSchema):
            captured["author_id"] = get_rel_id(request, "author")
            return 201, {"id": 1, "name": body.name, "author": {"id": int(captured["author_id"]), "name": "Alice"}}  # ty: ignore[invalid-argument-type]

        client = TestClient(api)
        response = client.post(
            "/items",
            json={
                "data": {
                    "type": "items",
                    "attributes": {"name": "New"},
                    "relationships": {
                        "author": {
                            "data": {"type": "people", "id": "42"},
                        }
                    },
                }
            },
            content_type="application/vnd.api+json",
        )

        assert response.status_code == 201
        assert captured["author_id"] == "42"


class TestNinjaJsonAPIPatch:
    def test_patch_unwraps_body(self):
        api = NinjaJsonAPI(urls_namespace="test-patch")

        captured = {}

        @api.patch("/items/{item_id}", response=SimpleSchema)
        def update_item(request, item_id: int, body: SimpleCreateSchema):
            captured["name"] = body.name
            return {"id": item_id, "name": body.name}

        client = TestClient(api)
        response = client.patch(
            "/items/1",
            json={
                "data": {
                    "type": "simples",
                    "attributes": {"name": "Updated"},
                }
            },
            content_type="application/vnd.api+json",
        )

        assert response.status_code == 200
        assert captured["name"] == "Updated"


class TestNinjaJsonAPIDelete:
    def test_delete_returns_204(self):
        api = NinjaJsonAPI(urls_namespace="test-delete")

        @api.delete("/items/{item_id}", response={204: None})
        def delete_item(request, item_id: int):
            return 204, None

        client = TestClient(api)
        response = client.delete("/items/1")

        assert response.status_code == 204


class TestNinjaJsonAPIStatusCodeResponse:
    def test_dict_response_with_status_codes(self):
        api = NinjaJsonAPI(urls_namespace="test-status-codes")

        @api.post("/items", response={201: SimpleSchema, 200: SimpleSchema})
        def create_or_return(request, body: SimpleCreateSchema):
            return 201, {"id": 1, "name": body.name}

        client = TestClient(api)
        response = client.post(
            "/items",
            json={
                "data": {
                    "type": "simples",
                    "attributes": {"name": "Test"},
                }
            },
            content_type="application/vnd.api+json",
        )

        assert response.status_code == 201
        assert response.json()["data"]["type"] == "simples"


class TestNinjaJsonAPIExceptionHandling:
    def test_http_exception_returns_jsonapi_error(self):
        api = NinjaJsonAPI(urls_namespace="test-exc")
        from django_ninja_jsonapi.exceptions import BadRequest

        @api.get("/fail")
        def fail(request):
            raise BadRequest(detail="Something went wrong")

        client = TestClient(api)
        response = client.get("/fail")

        assert response.status_code == 400
        data = response.json()
        assert "errors" in data

    def test_object_does_not_exist_returns_404(self):
        api = NinjaJsonAPI(urls_namespace="test-404")
        from django.core.exceptions import ObjectDoesNotExist

        @api.get("/missing")
        def missing(request):
            raise ObjectDoesNotExist("Item not found.")

        client = TestClient(api)
        response = client.get("/missing")

        assert response.status_code == 404
        data = response.json()
        assert "errors" in data


class TestNinjaJsonAPIPagination:
    def test_pagination_links_in_response(self):
        from django_ninja_jsonapi.response_helpers import jsonapi_paginate

        api = NinjaJsonAPI(urls_namespace="test-pagination")

        @api.get("/items", response=list[SimpleSchema])
        def list_items(request):
            items = [{"id": i, "name": f"Item {i}"} for i in range(1, 51)]
            return jsonapi_paginate(request, items)

        client = TestClient(api)
        response = client.get("/items?page[size]=10&page[number]=1")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 10
        assert "meta" in data
        assert data["meta"]["count"] == 50


class TestNinjaJsonAPINoMeta:
    """Test that schemas without explicit jsonapi_meta are passed through."""

    def test_schema_without_meta_not_transformed(self):
        api = NinjaJsonAPI(urls_namespace="test-no-meta")

        class PlainSchema(BaseModel):
            id: int
            name: str

        @api.get("/plain/{id}", response=PlainSchema)
        def get_plain(request, id: int):
            return {"id": id, "name": "plain"}

        client = TestClient(api)
        response = client.get("/plain/1")

        # Without jsonapi_meta, the response should NOT be wrapped in JSON:API format
        data = response.json()
        assert data == {"id": 1, "name": "plain"}


class TestApplyAttributesWithNewStyle:
    def test_apply_attributes_plain_schema(self):
        from django_ninja_jsonapi.helpers import apply_attributes

        class FakeModel:
            name = "old"
            title = "old"

            def save(self, update_fields=None):
                self.saved_fields = update_fields

        class UpdateSchema(BaseModel):
            name: str | None = None
            title: str | None = None

        instance = FakeModel()
        body = UpdateSchema(name="new")
        attrs = apply_attributes(instance, body, save=False)

        assert attrs == {"name": "new"}
        assert instance.name == "new"
        assert instance.title == "old"

    def test_apply_attributes_legacy_style(self):
        from django_ninja_jsonapi.helpers import apply_attributes
        from django_ninja_jsonapi.schema_factory import jsonapi_body

        class UpdateSchema(BaseModel):
            name: str | None = None

        BodyModel = jsonapi_body(UpdateSchema, "things")

        class FakeModel:
            name = "old"

            def save(self, update_fields=None):
                self.saved_fields = update_fields

        body = BodyModel.model_validate({"data": {"type": "things", "attributes": {"name": "new"}}})
        instance = FakeModel()
        attrs = apply_attributes(instance, body, save=False)

        assert attrs == {"name": "new"}
        assert instance.name == "new"
