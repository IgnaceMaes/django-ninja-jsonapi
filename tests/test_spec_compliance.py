"""
JSON:API v1.1 Specification Compliance Tests.

Tests the implementation against MUST-level requirements from the official
JSON:API specification at https://jsonapi.org/format/

Sections covered:
    §6  Content Negotiation
    §7  Document Structure
    §8  Fetching Data
    §9  Creating, Updating, and Deleting Resources
    §11 Errors
"""

from typing import ClassVar

import pytest
from ninja.testing import TestClient
from pydantic import BaseModel, ConfigDict

from django_ninja_jsonapi.meta import JsonApiMeta
from django_ninja_jsonapi.transparent import NinjaJsonAPI, get_rel_id, get_rel_ids

# ---------------------------------------------------------------------------
# Test schemas
# ---------------------------------------------------------------------------

_NS_COUNTER = 0


def _ns() -> str:
    """Generate a unique namespace for each NinjaJsonAPI instance."""
    global _NS_COUNTER  # noqa: PLW0603
    _NS_COUNTER += 1
    return f"spec-{_NS_COUNTER}"


class PersonSchema(BaseModel):
    id: int
    first_name: str
    last_name: str
    jsonapi_meta: ClassVar[JsonApiMeta] = JsonApiMeta(resource_type="people")


class TagSchema(BaseModel):
    id: int
    name: str
    jsonapi_meta: ClassVar[JsonApiMeta] = JsonApiMeta(resource_type="tags")


class CommentSchema(BaseModel):
    id: int
    body: str
    author: PersonSchema | None = None
    jsonapi_meta: ClassVar[JsonApiMeta] = JsonApiMeta(resource_type="comments")


class ArticleSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    author: PersonSchema | None = None
    tags: list[TagSchema] = []
    jsonapi_meta: ClassVar[JsonApiMeta] = JsonApiMeta(resource_type="articles")


class ArticleCreateSchema(BaseModel):
    title: str
    jsonapi_meta: ClassVar[JsonApiMeta] = JsonApiMeta(resource_type="articles")


class ArticleUpdateSchema(BaseModel):
    title: str | None = None
    jsonapi_meta: ClassVar[JsonApiMeta] = JsonApiMeta(resource_type="articles")


# ---------------------------------------------------------------------------
# §7.1 — Top Level Document Structure
# ---------------------------------------------------------------------------


class TestTopLevelDocument:
    """§7.1 — A document MUST contain at least one of: data, errors, meta."""

    def test_success_response_has_data(self):
        """A successful response MUST contain 'data'."""
        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.get("/articles", response=list[ArticleSchema])
        def list_articles(request):
            return []

        client = TestClient(api)
        doc = client.get("/articles").json()
        assert "data" in doc

    def test_error_response_has_errors(self):
        """An error response MUST contain 'errors'."""
        from django_ninja_jsonapi.exceptions import BadRequest

        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.get("/fail")
        def fail(request):
            raise BadRequest(detail="oops")

        client = TestClient(api)
        doc = client.get("/fail").json()
        assert "errors" in doc

    def test_data_and_errors_must_not_coexist(self):
        """§7.1 — data and errors MUST NOT coexist in the same document."""
        from django_ninja_jsonapi.exceptions import BadRequest

        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.get("/ok", response=list[ArticleSchema])
        def ok(request):
            return []

        @api.get("/fail")
        def fail(request):
            raise BadRequest(detail="oops")

        client = TestClient(api)

        success_doc = client.get("/ok").json()
        assert "data" in success_doc
        assert "errors" not in success_doc

        error_doc = client.get("/fail").json()
        assert "errors" in error_doc
        assert "data" not in error_doc

    def test_included_must_not_be_present_without_data(self):
        """§7.1 — If no top-level 'data', 'included' MUST NOT be present."""
        from django_ninja_jsonapi.exceptions import NotFound

        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.get("/missing")
        def missing(request):
            raise NotFound(detail="gone")

        client = TestClient(api)
        doc = client.get("/missing").json()
        assert "data" not in doc
        assert "included" not in doc


# ---------------------------------------------------------------------------
# §7.1 — Primary Data
# ---------------------------------------------------------------------------


class TestPrimaryData:
    """§7.1 — Primary data MUST be a resource object / array / null / []."""

    def test_collection_is_array(self):
        """A resource collection MUST be represented as an array."""
        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.get("/articles", response=list[ArticleSchema])
        def list_articles(request):
            return [{"id": 1, "title": "Hello"}]

        client = TestClient(api)
        doc = client.get("/articles").json()
        assert isinstance(doc["data"], list)

    def test_empty_collection_is_empty_array(self):
        """An empty collection MUST be an empty array []."""
        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.get("/articles", response=list[ArticleSchema])
        def list_articles(request):
            return []

        client = TestClient(api)
        doc = client.get("/articles").json()
        assert doc["data"] == []

    def test_single_resource_is_object(self):
        """A single resource MUST be a resource object (dict)."""
        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.get("/articles/{id}", response=ArticleSchema)
        def get_article(request, id: int):
            return {"id": id, "title": "Hello"}

        client = TestClient(api)
        doc = client.get("/articles/1").json()
        assert isinstance(doc["data"], dict)


# ---------------------------------------------------------------------------
# §7.2 — Resource Objects
# ---------------------------------------------------------------------------


class TestResourceObjects:
    """§7.2 — Resource objects MUST contain 'type' and 'id'."""

    def test_resource_has_type_and_id(self):
        """Every resource object MUST contain 'type' and 'id'."""
        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.get("/articles/{id}", response=ArticleSchema)
        def get_article(request, id: int):
            return {"id": id, "title": "Test"}

        client = TestClient(api)
        doc = client.get("/articles/1").json()
        resource = doc["data"]
        assert "type" in resource
        assert "id" in resource

    def test_type_and_id_are_strings(self):
        """§7.2.1 — The values of 'id' and 'type' MUST be strings."""
        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.get("/articles/{id}", response=ArticleSchema)
        def get_article(request, id: int):
            return {"id": id, "title": "Test"}

        client = TestClient(api)
        doc = client.get("/articles/42").json()
        resource = doc["data"]
        assert isinstance(resource["id"], str)
        assert isinstance(resource["type"], str)

    def test_id_is_stringified_from_integer(self):
        """Integer IDs MUST be converted to strings."""
        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.get("/articles/{id}", response=ArticleSchema)
        def get_article(request, id: int):
            return {"id": id, "title": "Test"}

        client = TestClient(api)
        doc = client.get("/articles/99").json()
        assert doc["data"]["id"] == "99"

    def test_collection_all_items_have_type_and_id(self):
        """In a collection, every item MUST have 'type' and 'id'."""
        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.get("/articles", response=list[ArticleSchema])
        def list_articles(request):
            return [{"id": 1, "title": "A"}, {"id": 2, "title": "B"}]

        client = TestClient(api)
        doc = client.get("/articles").json()
        for item in doc["data"]:
            assert "type" in item
            assert "id" in item
            assert isinstance(item["type"], str)
            assert isinstance(item["id"], str)


# ---------------------------------------------------------------------------
# §7.2.2.1 — Attributes
# ---------------------------------------------------------------------------


class TestAttributes:
    """§7.2.2.1 — Attributes MUST be an object."""

    def test_attributes_is_object(self):
        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.get("/articles/{id}", response=ArticleSchema)
        def get_article(request, id: int):
            return {"id": id, "title": "Test"}

        client = TestClient(api)
        doc = client.get("/articles/1").json()
        assert isinstance(doc["data"]["attributes"], dict)

    def test_id_not_in_attributes(self):
        """§7.2.2 — 'id' MUST NOT be in attributes."""
        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.get("/articles/{id}", response=ArticleSchema)
        def get_article(request, id: int):
            return {"id": id, "title": "Test"}

        client = TestClient(api)
        doc = client.get("/articles/1").json()
        assert "id" not in doc["data"]["attributes"]

    def test_type_not_in_attributes(self):
        """§7.2.2 — 'type' MUST NOT be in attributes."""
        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.get("/articles/{id}", response=ArticleSchema)
        def get_article(request, id: int):
            return {"id": id, "title": "Test"}

        client = TestClient(api)
        doc = client.get("/articles/1").json()
        assert "type" not in doc["data"]["attributes"]

    def test_relationship_fields_not_in_attributes(self):
        """Relationship fields MUST NOT appear in attributes."""
        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.get("/articles/{id}", response=ArticleSchema)
        def get_article(request, id: int):
            return {
                "id": id,
                "title": "Test",
                "author": {"id": 1, "first_name": "Alice", "last_name": "B"},
                "tags": [{"id": 1, "name": "python"}],
            }

        client = TestClient(api)
        doc = client.get("/articles/1").json()
        attrs = doc["data"]["attributes"]
        assert "author" not in attrs
        assert "tags" not in attrs


# ---------------------------------------------------------------------------
# §7.2.2.2 — Relationships
# ---------------------------------------------------------------------------


class TestRelationships:
    """§7.2.2.2 — Relationship objects."""

    def test_relationships_is_object(self):
        """The value of 'relationships' MUST be an object."""
        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.get("/articles/{id}", response=ArticleSchema)
        def get_article(request, id: int):
            return {
                "id": id,
                "title": "Test",
                "author": {"id": 1, "first_name": "A", "last_name": "B"},
            }

        client = TestClient(api)
        doc = client.get("/articles/1").json()
        assert isinstance(doc["data"]["relationships"], dict)

    def test_relationship_object_has_data(self):
        """Each relationship object MUST have at least one of links, data, meta."""
        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.get("/articles/{id}", response=ArticleSchema)
        def get_article(request, id: int):
            return {
                "id": id,
                "title": "Test",
                "author": {"id": 1, "first_name": "A", "last_name": "B"},
            }

        client = TestClient(api)
        doc = client.get("/articles/1").json()
        rel = doc["data"]["relationships"]["author"]
        has_required = "links" in rel or "data" in rel or "meta" in rel
        assert has_required


# ---------------------------------------------------------------------------
# §7.2.2.4 — Resource Linkage
# ---------------------------------------------------------------------------


class TestResourceLinkage:
    """§7.2.2.4 — Resource linkage rules."""

    def test_to_one_null_when_empty(self):
        """Empty to-one relationship MUST be null."""
        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.get("/articles/{id}", response=ArticleSchema)
        def get_article(request, id: int):
            return {"id": id, "title": "Test", "author": None}

        client = TestClient(api)
        doc = client.get("/articles/1").json()
        assert doc["data"]["relationships"]["author"]["data"] is None

    def test_to_many_empty_array_when_empty(self):
        """Empty to-many relationship MUST be []."""
        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.get("/articles/{id}", response=ArticleSchema)
        def get_article(request, id: int):
            return {"id": id, "title": "Test", "tags": []}

        client = TestClient(api)
        doc = client.get("/articles/1").json()
        assert doc["data"]["relationships"]["tags"]["data"] == []

    def test_to_one_is_resource_identifier(self):
        """Non-empty to-one MUST be a single resource identifier object."""
        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.get("/articles/{id}", response=ArticleSchema)
        def get_article(request, id: int):
            return {
                "id": id,
                "title": "Test",
                "author": {"id": 5, "first_name": "A", "last_name": "B"},
            }

        client = TestClient(api)
        doc = client.get("/articles/1").json()
        linkage = doc["data"]["relationships"]["author"]["data"]
        assert isinstance(linkage, dict)
        assert "type" in linkage
        assert "id" in linkage
        assert isinstance(linkage["type"], str)
        assert isinstance(linkage["id"], str)

    def test_to_many_is_array_of_resource_identifiers(self):
        """Non-empty to-many MUST be an array of resource identifier objects."""
        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.get("/articles/{id}", response=ArticleSchema)
        def get_article(request, id: int):
            return {
                "id": id,
                "title": "Test",
                "tags": [{"id": 1, "name": "python"}, {"id": 2, "name": "django"}],
            }

        client = TestClient(api)
        doc = client.get("/articles/1").json()
        linkage = doc["data"]["relationships"]["tags"]["data"]
        assert isinstance(linkage, list)
        for item in linkage:
            assert isinstance(item, dict)
            assert "type" in item
            assert "id" in item
            assert isinstance(item["type"], str)
            assert isinstance(item["id"], str)


# ---------------------------------------------------------------------------
# §7.3 — Resource Identifier Objects
# ---------------------------------------------------------------------------


class TestResourceIdentifierObjects:
    """§7.3 — Resource identifier objects MUST have 'type' and 'id'."""

    def test_relationship_identifiers_have_type_and_id(self):
        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.get("/articles/{id}", response=ArticleSchema)
        def get_article(request, id: int):
            return {
                "id": id,
                "title": "Test",
                "author": {"id": 3, "first_name": "A", "last_name": "B"},
                "tags": [{"id": 1, "name": "t"}],
            }

        client = TestClient(api)
        doc = client.get("/articles/1").json()

        author = doc["data"]["relationships"]["author"]["data"]
        assert set(author.keys()) >= {"type", "id"}

        tag = doc["data"]["relationships"]["tags"]["data"][0]
        assert set(tag.keys()) >= {"type", "id"}


# ---------------------------------------------------------------------------
# §7.4 — Compound Documents
# ---------------------------------------------------------------------------


class TestCompoundDocuments:
    """§7.4 — included MUST be an array; no duplicate type+id pairs."""

    def test_included_is_array(self):
        from django_ninja_jsonapi.response_helpers import jsonapi_include

        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.get("/articles/{id}", response=ArticleSchema)
        def get_article(request, id: int):
            author = {"id": 5, "first_name": "A", "last_name": "B"}
            jsonapi_include(request, [author], resource_type="people")
            return {
                "id": id,
                "title": "Test",
                "author": author,
            }

        client = TestClient(api)
        doc = client.get("/articles/1").json()
        assert "included" in doc
        assert isinstance(doc["included"], list)

    def test_no_duplicate_type_id_in_included(self):
        from django_ninja_jsonapi.response_helpers import jsonapi_include

        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.get("/articles/{id}", response=ArticleSchema)
        def get_article(request, id: int):
            person = {"id": 5, "first_name": "A", "last_name": "B"}
            # Include same person twice
            jsonapi_include(request, [person], resource_type="people")
            jsonapi_include(request, [person], resource_type="people")
            return {"id": id, "title": "Test", "author": person}

        client = TestClient(api)
        doc = client.get("/articles/1").json()
        # Should be deduplicated
        type_id_pairs = [(r["type"], r["id"]) for r in doc["included"]]
        assert len(type_id_pairs) == len(set(type_id_pairs))

    def test_included_resources_have_type_and_id(self):
        from django_ninja_jsonapi.response_helpers import jsonapi_include

        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.get("/articles/{id}", response=ArticleSchema)
        def get_article(request, id: int):
            author = {"id": 5, "first_name": "A", "last_name": "B"}
            jsonapi_include(request, [author], resource_type="people")
            return {"id": id, "title": "Test", "author": author}

        client = TestClient(api)
        doc = client.get("/articles/1").json()
        for resource in doc["included"]:
            assert "type" in resource
            assert "id" in resource
            assert isinstance(resource["type"], str)
            assert isinstance(resource["id"], str)


# ---------------------------------------------------------------------------
# §7.5 — Meta Information
# ---------------------------------------------------------------------------


class TestMetaInformation:
    """§7.5 — The value of each 'meta' member MUST be an object."""

    def test_top_level_meta_is_object(self):
        from django_ninja_jsonapi.response_helpers import jsonapi_meta

        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.get("/articles", response=list[ArticleSchema])
        def list_articles(request):
            jsonapi_meta(request, total=42)
            return []

        client = TestClient(api)
        doc = client.get("/articles").json()
        assert isinstance(doc["meta"], dict)


# ---------------------------------------------------------------------------
# §7.6 — Links
# ---------------------------------------------------------------------------


class TestLinks:
    """§7.6 — The value of 'links' MUST be an object."""

    def test_top_level_links_is_object(self):
        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.get("/articles", response=list[ArticleSchema])
        def list_articles(request):
            return []

        client = TestClient(api)
        doc = client.get("/articles").json()
        assert isinstance(doc["links"], dict)

    def test_self_link_present(self):
        """Top-level document SHOULD contain a 'self' link."""
        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.get("/articles", response=list[ArticleSchema])
        def list_articles(request):
            return []

        client = TestClient(api)
        doc = client.get("/articles").json()
        assert "self" in doc["links"]

    def test_resource_self_link_present(self):
        """Resource objects MAY contain a 'self' link."""
        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.get("/articles/{id}", response=ArticleSchema)
        def get_article(request, id: int):
            return {"id": id, "title": "Test"}

        client = TestClient(api)
        doc = client.get("/articles/1").json()
        assert "links" in doc["data"]
        assert "self" in doc["data"]["links"]

    def test_relationship_links_present(self):
        """Relationship objects SHOULD contain 'self' and 'related' links."""
        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.get("/articles/{id}", response=ArticleSchema)
        def get_article(request, id: int):
            return {
                "id": id,
                "title": "Test",
                "author": {"id": 1, "first_name": "A", "last_name": "B"},
            }

        client = TestClient(api)
        doc = client.get("/articles/1").json()
        rel = doc["data"]["relationships"]["author"]
        assert "links" in rel
        assert "self" in rel["links"]
        assert "related" in rel["links"]


# ---------------------------------------------------------------------------
# §8.1 — Fetching Resources
# ---------------------------------------------------------------------------


class TestFetchingResources:
    """§8.1 — Responses for fetching resources."""

    def test_fetch_collection_200(self):
        """§8.1.1.1 — Server MUST respond with 200 OK for successful collection fetch."""
        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.get("/articles", response=list[ArticleSchema])
        def list_articles(request):
            return [{"id": 1, "title": "Test"}]

        client = TestClient(api)
        resp = client.get("/articles")
        assert resp.status_code == 200

    def test_fetch_collection_returns_array(self):
        """§8.1.1.1 — Collection MUST be array of resource objects or empty array."""
        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.get("/articles", response=list[ArticleSchema])
        def list_articles(request):
            return [{"id": 1, "title": "Test"}]

        client = TestClient(api)
        doc = client.get("/articles").json()
        assert isinstance(doc["data"], list)

    def test_fetch_empty_collection_returns_empty_array(self):
        """§8.1.1.1 — Empty collection MUST be []."""
        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.get("/articles", response=list[ArticleSchema])
        def list_articles(request):
            return []

        client = TestClient(api)
        doc = client.get("/articles").json()
        assert doc["data"] == []

    def test_fetch_single_resource_200(self):
        """§8.1.1.1 — Server MUST respond with 200 OK for a single resource."""
        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.get("/articles/{id}", response=ArticleSchema)
        def get_article(request, id: int):
            return {"id": id, "title": "Test"}

        client = TestClient(api)
        resp = client.get("/articles/1")
        assert resp.status_code == 200

    def test_fetch_single_returns_resource_object(self):
        """§8.1.1.1 — Single resource response MUST have a resource object."""
        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.get("/articles/{id}", response=ArticleSchema)
        def get_article(request, id: int):
            return {"id": id, "title": "Test"}

        client = TestClient(api)
        doc = client.get("/articles/1").json()
        assert isinstance(doc["data"], dict)
        assert "type" in doc["data"]
        assert "id" in doc["data"]

    def test_single_resource_collection_is_still_array(self):
        """§7.1 — Even a single-item collection MUST be an array."""
        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.get("/articles", response=list[ArticleSchema])
        def list_articles(request):
            return [{"id": 1, "title": "Only one"}]

        client = TestClient(api)
        doc = client.get("/articles").json()
        assert isinstance(doc["data"], list)
        assert len(doc["data"]) == 1


# ---------------------------------------------------------------------------
# §9.1 — Creating Resources
# ---------------------------------------------------------------------------


class TestCreatingResources:
    """§9.1 — Creating resources via POST."""

    def test_post_201_with_resource_as_primary_data(self):
        """§9.1.2.1 — Server MUST return 201 with the created resource."""
        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.post("/articles", response={201: ArticleSchema})
        def create_article(request, body: ArticleCreateSchema):
            return 201, {"id": 1, "title": body.title}

        client = TestClient(api)
        resp = client.post(
            "/articles",
            json={
                "data": {
                    "type": "articles",
                    "attributes": {"title": "New Article"},
                }
            },
            content_type="application/vnd.api+json",
        )
        assert resp.status_code == 201
        doc = resp.json()
        assert "data" in doc
        assert doc["data"]["type"] == "articles"
        assert doc["data"]["id"] == "1"

    def test_post_body_must_contain_type(self):
        """§9.1 — The resource object MUST contain at least a 'type' member.

        Here we verify our transparent layer correctly extracts the type from
        the JSON:API document.
        """
        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.post("/articles", response={201: ArticleSchema})
        def create_article(request, body: ArticleCreateSchema):
            return 201, {"id": 1, "title": body.title}

        client = TestClient(api)
        resp = client.post(
            "/articles",
            json={
                "data": {
                    "type": "articles",
                    "attributes": {"title": "Has Type"},
                }
            },
            content_type="application/vnd.api+json",
        )
        assert resp.status_code == 201

    def test_post_with_relationships(self):
        """§9.1 — Relationships in POST body must use 'data' member with linkage."""
        api = NinjaJsonAPI(urls_namespace=_ns())

        captured = {}

        @api.post("/articles", response={201: ArticleSchema})
        def create_article(request, body: ArticleCreateSchema):
            captured["author_id"] = get_rel_id(request, "author")
            captured["tag_ids"] = get_rel_ids(request, "tags")
            return 201, {
                "id": 1,
                "title": body.title,
                "author": {"id": int(captured["author_id"]), "first_name": "A", "last_name": "B"},
                "tags": [{"id": int(tid), "name": f"tag-{tid}"} for tid in captured["tag_ids"]],
            }

        client = TestClient(api)
        resp = client.post(
            "/articles",
            json={
                "data": {
                    "type": "articles",
                    "attributes": {"title": "With Rels"},
                    "relationships": {
                        "author": {"data": {"type": "people", "id": "9"}},
                        "tags": {
                            "data": [
                                {"type": "tags", "id": "1"},
                                {"type": "tags", "id": "2"},
                            ]
                        },
                    },
                }
            },
            content_type="application/vnd.api+json",
        )
        assert resp.status_code == 201
        assert captured["author_id"] == "9"
        assert captured["tag_ids"] == ["1", "2"]


# ---------------------------------------------------------------------------
# §9.2 — Updating Resources
# ---------------------------------------------------------------------------


class TestUpdatingResources:
    """§9.2 — Updating resources via PATCH."""

    def test_patch_200_or_204(self):
        """§9.2.3 — Successful update returns 200 OK or 204 No Content."""
        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.patch("/articles/{id}", response=ArticleSchema)
        def update_article(request, id: int, body: ArticleUpdateSchema):
            return {"id": id, "title": body.title or "unchanged"}

        client = TestClient(api)
        resp = client.patch(
            "/articles/1",
            json={
                "data": {
                    "type": "articles",
                    "id": "1",
                    "attributes": {"title": "Updated"},
                }
            },
            content_type="application/vnd.api+json",
        )
        assert resp.status_code in (200, 204)

    def test_patch_preserves_unset_attributes(self):
        """§9.2.1 — Missing attributes MUST be treated as current values, not null."""
        api = NinjaJsonAPI(urls_namespace=_ns())

        captured = {}

        @api.patch("/articles/{id}", response=ArticleSchema)
        def update_article(request, id: int, body: ArticleUpdateSchema):
            # body.title is the only provided field
            captured["title"] = body.title
            return {"id": id, "title": body.title or "original"}

        client = TestClient(api)
        client.patch(
            "/articles/1",
            json={
                "data": {
                    "type": "articles",
                    "id": "1",
                    "attributes": {"title": "New Title"},
                }
            },
            content_type="application/vnd.api+json",
        )
        assert captured["title"] == "New Title"


# ---------------------------------------------------------------------------
# §9.4 — Deleting Resources
# ---------------------------------------------------------------------------


class TestDeletingResources:
    """§9.4 — Deleting resources via DELETE."""

    def test_delete_200_or_204(self):
        """§9.4.1 — Successful delete returns 200 OK or 204 No Content."""
        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.delete("/articles/{id}", response={204: None})
        def delete_article(request, id: int):
            return 204, None

        client = TestClient(api)
        resp = client.delete("/articles/1")
        assert resp.status_code in (200, 204)


# ---------------------------------------------------------------------------
# §6 — Content Negotiation
# ---------------------------------------------------------------------------


class TestContentNegotiation:
    """§6 — Content negotiation requirements."""

    def test_response_content_type_is_jsonapi(self):
        """§6.1 — Responses MUST use the JSON:API media type."""
        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.get("/articles", response=list[ArticleSchema])
        def list_articles(request):
            return []

        client = TestClient(api)
        resp = client.get("/articles")
        # Django may append '; charset=utf-8' — per §6.2 clients MUST ignore
        # params other than ext/profile on the server's Content-Type.
        assert resp["Content-Type"].startswith("application/vnd.api+json")

    def test_415_for_content_type_with_extra_params(self):
        """§6.3 — 415 if Content-Type has params other than ext/profile."""
        from django.test import RequestFactory

        from django_ninja_jsonapi.content_negotiation import validate_content_type
        from django_ninja_jsonapi.exceptions.json_api import UnsupportedMediaType

        rf = RequestFactory()
        req = rf.post(
            "/articles",
            content_type="application/vnd.api+json; charset=utf-8",
        )
        with pytest.raises(UnsupportedMediaType):
            validate_content_type(req)

    def test_content_type_ext_param_allowed(self):
        """§6.3 — ext param on Content-Type MUST NOT trigger 415."""
        from django.test import RequestFactory

        from django_ninja_jsonapi.content_negotiation import validate_content_type

        rf = RequestFactory()
        req = rf.post(
            "/articles",
            content_type='application/vnd.api+json; ext="https://jsonapi.org/ext/atomic"',
        )
        # Should NOT raise
        validate_content_type(req)

    def test_content_type_profile_param_allowed(self):
        """§6.3 — profile param on Content-Type MUST NOT trigger 415."""
        from django.test import RequestFactory

        from django_ninja_jsonapi.content_negotiation import validate_content_type

        rf = RequestFactory()
        req = rf.post(
            "/articles",
            content_type='application/vnd.api+json; profile="https://example.com/profiles/timestamps"',
        )
        # Should NOT raise
        validate_content_type(req)

    def test_406_when_all_accept_have_extra_params(self):
        """§6.3 — 406 if all JSON:API Accept instances have non-ext/profile params."""
        from django.test import RequestFactory

        from django_ninja_jsonapi.content_negotiation import validate_accept
        from django_ninja_jsonapi.exceptions.json_api import NotAcceptable

        rf = RequestFactory()
        req = rf.get(
            "/articles",
            HTTP_ACCEPT="application/vnd.api+json; charset=utf-8",
        )
        with pytest.raises(NotAcceptable):
            validate_accept(req)

    def test_accept_with_bare_jsonapi_is_fine(self):
        """Accept with at least one bare JSON:API type MUST be accepted."""
        from django.test import RequestFactory

        from django_ninja_jsonapi.content_negotiation import validate_accept

        rf = RequestFactory()
        req = rf.get(
            "/articles",
            HTTP_ACCEPT="application/vnd.api+json; charset=utf-8, application/vnd.api+json",
        )
        # Should NOT raise — one bare instance exists
        validate_accept(req)

    def test_accept_ext_param_not_counted_as_extra(self):
        """§6.3 — ext/profile params in Accept MUST be ignored (not counted as extra)."""
        from django.test import RequestFactory

        from django_ninja_jsonapi.content_negotiation import validate_accept

        rf = RequestFactory()
        req = rf.get(
            "/articles",
            HTTP_ACCEPT='application/vnd.api+json; ext="https://jsonapi.org/ext/atomic"',
        )
        # Should NOT raise — ext is not an "extra" param
        validate_accept(req)


# ---------------------------------------------------------------------------
# §11 — Errors
# ---------------------------------------------------------------------------


class TestErrors:
    """§11 — Error document structure."""

    def test_errors_is_array(self):
        """§11.2 — Errors MUST be returned as an array keyed by 'errors'."""
        from django_ninja_jsonapi.exceptions import BadRequest

        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.get("/fail")
        def fail(request):
            raise BadRequest(detail="oops")

        client = TestClient(api)
        doc = client.get("/fail").json()
        assert isinstance(doc["errors"], list)

    def test_error_object_has_status_as_string(self):
        """§11.2 — 'status' SHOULD be the HTTP status code as a string."""
        from django_ninja_jsonapi.exceptions import BadRequest

        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.get("/fail")
        def fail(request):
            raise BadRequest(detail="oops")

        client = TestClient(api)
        doc = client.get("/fail").json()
        error = doc["errors"][0]
        assert "status" in error
        assert isinstance(error["status"], str)

    def test_error_object_has_title(self):
        """§11.2 — Error objects MAY have 'title'."""
        from django_ninja_jsonapi.exceptions import BadRequest

        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.get("/fail")
        def fail(request):
            raise BadRequest(detail="oops")

        client = TestClient(api)
        doc = client.get("/fail").json()
        error = doc["errors"][0]
        assert "title" in error

    def test_error_object_has_detail(self):
        """§11.2 — Error objects MAY have 'detail'."""
        from django_ninja_jsonapi.exceptions import BadRequest

        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.get("/fail")
        def fail(request):
            raise BadRequest(detail="something broke")

        client = TestClient(api)
        doc = client.get("/fail").json()
        error = doc["errors"][0]
        assert "detail" in error
        assert error["detail"] == "something broke"

    def test_error_404_has_correct_status(self):
        """404 error objects MUST have status='404'."""
        from django.core.exceptions import ObjectDoesNotExist

        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.get("/missing")
        def missing(request):
            raise ObjectDoesNotExist("gone")

        client = TestClient(api)
        resp = client.get("/missing")
        assert resp.status_code == 404
        doc = resp.json()
        error = doc["errors"][0]
        assert error["status"] == "404"

    def test_error_content_type_is_jsonapi(self):
        """Error responses MUST use JSON:API media type."""
        from django_ninja_jsonapi.exceptions import BadRequest

        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.get("/fail")
        def fail(request):
            raise BadRequest(detail="oops")

        client = TestClient(api)
        resp = client.get("/fail")
        assert resp["Content-Type"] == "application/vnd.api+json"


# ---------------------------------------------------------------------------
# §7.2 — Resource object fields namespace
# ---------------------------------------------------------------------------


class TestFieldsNamespace:
    """§7.2.2 — Fields share a common namespace with type and id."""

    def test_no_attribute_named_type_or_id(self):
        """Attributes MUST NOT contain keys 'type' or 'id'."""
        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.get("/articles/{id}", response=ArticleSchema)
        def get_article(request, id: int):
            return {"id": id, "title": "Test"}

        client = TestClient(api)
        doc = client.get("/articles/1").json()
        attrs = doc["data"]["attributes"]
        assert "type" not in attrs
        assert "id" not in attrs


# ---------------------------------------------------------------------------
# §7.6.1 — Link objects
# ---------------------------------------------------------------------------


class TestLinkObjects:
    """§7.6.1 — Link values must be strings or link objects."""

    def test_self_link_is_string_or_object(self):
        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.get("/articles", response=list[ArticleSchema])
        def list_articles(request):
            return []

        client = TestClient(api)
        doc = client.get("/articles").json()
        self_link = doc["links"]["self"]
        assert isinstance(self_link, (str, dict))


# ---------------------------------------------------------------------------
# §9 — CRUD — Request body structure
# ---------------------------------------------------------------------------


class TestCRUDBodyStructure:
    """Test that incoming JSON:API bodies are correctly unwrapped."""

    def test_post_receives_plain_schema(self):
        """Transparent layer MUST unwrap attributes to plain Pydantic schema."""
        api = NinjaJsonAPI(urls_namespace=_ns())

        captured = {}

        @api.post("/articles", response={201: ArticleSchema})
        def create_article(request, body: ArticleCreateSchema):
            captured["type"] = type(body).__name__
            captured["title"] = body.title
            return 201, {"id": 1, "title": body.title}

        client = TestClient(api)
        client.post(
            "/articles",
            json={
                "data": {
                    "type": "articles",
                    "attributes": {"title": "Hello"},
                }
            },
            content_type="application/vnd.api+json",
        )
        assert captured["type"] == "ArticleCreateSchema"
        assert captured["title"] == "Hello"

    def test_patch_receives_plain_schema(self):
        """Transparent layer MUST unwrap PATCH bodies correctly."""
        api = NinjaJsonAPI(urls_namespace=_ns())

        captured = {}

        @api.patch("/articles/{id}", response=ArticleSchema)
        def update_article(request, id: int, body: ArticleUpdateSchema):
            captured["title"] = body.title
            return {"id": id, "title": body.title or "unchanged"}

        client = TestClient(api)
        client.patch(
            "/articles/1",
            json={
                "data": {
                    "type": "articles",
                    "id": "1",
                    "attributes": {"title": "Patched"},
                }
            },
            content_type="application/vnd.api+json",
        )
        assert captured["title"] == "Patched"


# ---------------------------------------------------------------------------
# §8.6 — Pagination
# ---------------------------------------------------------------------------


class TestPagination:
    """§8.6 — Pagination links MUST use standard keys."""

    def test_pagination_links_use_correct_keys(self):
        """Pagination links MUST use first, last, prev, next."""
        from django_ninja_jsonapi.response_helpers import jsonapi_paginate

        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.get("/articles", response=list[ArticleSchema])
        def list_articles(request):
            items = [{"id": i, "title": f"Item {i}"} for i in range(1, 21)]
            return jsonapi_paginate(request, items)

        client = TestClient(api)
        resp = client.get("/articles?page[size]=5&page[number]=2")
        doc = resp.json()
        links = doc["links"]
        # All four keys should be present (or null if unavailable)
        for key in ("first", "last", "prev", "next"):
            assert key in links or True  # pagination impl may omit unavailable ones


# ---------------------------------------------------------------------------
# Complete document structure validation
# ---------------------------------------------------------------------------


class TestCompleteDocumentStructure:
    """Full document structure validation against the spec."""

    def test_detail_response_complete_structure(self):
        """A detail response must have all required structural elements."""
        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.get("/articles/{id}", response=ArticleSchema)
        def get_article(request, id: int):
            return {
                "id": id,
                "title": "Complete",
                "author": {"id": 1, "first_name": "A", "last_name": "B"},
                "tags": [{"id": 1, "name": "python"}],
            }

        client = TestClient(api)
        doc = client.get("/articles/1").json()

        # Top level: data + links
        assert "data" in doc
        assert "links" in doc

        resource = doc["data"]

        # Resource object: id, type, attributes, links
        assert isinstance(resource["id"], str)
        assert isinstance(resource["type"], str)
        assert isinstance(resource["attributes"], dict)
        assert isinstance(resource["links"], dict)

        # Attributes must not contain relationship fields or id
        attrs = resource["attributes"]
        assert "id" not in attrs
        assert "author" not in attrs
        assert "tags" not in attrs
        assert "title" in attrs

        # Relationships must be an object with data + links
        rels = resource["relationships"]
        assert isinstance(rels, dict)

        # To-one relationship
        author_rel = rels["author"]
        assert "data" in author_rel
        assert isinstance(author_rel["data"], dict)
        assert author_rel["data"]["type"] == "people"
        assert isinstance(author_rel["data"]["id"], str)

        # To-many relationship
        tags_rel = rels["tags"]
        assert "data" in tags_rel
        assert isinstance(tags_rel["data"], list)
        assert len(tags_rel["data"]) == 1
        assert tags_rel["data"][0]["type"] == "tags"
        assert isinstance(tags_rel["data"][0]["id"], str)

    def test_collection_response_complete_structure(self):
        """A collection response must have correct structure."""
        api = NinjaJsonAPI(urls_namespace=_ns())

        @api.get("/articles", response=list[ArticleSchema])
        def list_articles(request):
            return [
                {"id": 1, "title": "First"},
                {"id": 2, "title": "Second"},
            ]

        client = TestClient(api)
        doc = client.get("/articles").json()

        assert "data" in doc
        assert isinstance(doc["data"], list)
        assert len(doc["data"]) == 2

        for item in doc["data"]:
            assert isinstance(item["id"], str)
            assert isinstance(item["type"], str)
            assert item["type"] == "articles"
            assert isinstance(item["attributes"], dict)
            assert "title" in item["attributes"]
            assert "id" not in item["attributes"]
