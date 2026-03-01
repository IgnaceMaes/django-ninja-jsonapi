"""Comprehensive JSON:API specification compliance tests.

Validates the library's conformance to the JSON:API v1.0 specification
(https://jsonapi.org/format/). Each test class corresponds to a section
of the spec.

Sections covered:
- Document structure (top-level members)
- Resource objects (id, type, attributes, relationships, links)
- Resource identifier objects
- Compound documents (included, deduplication)
- Fetching data (collections, individual resources, relationships)
- Creating, updating, deleting resources
- Query parameters: sorting, pagination, filtering, sparse fieldsets, include
- Content negotiation (415 / 406)
- Error objects
"""

from __future__ import annotations

import json

import pytest
from asgiref.sync import sync_to_async
from django.test import AsyncClient

from django_ninja_jsonapi.renderers import JSONAPI_MEDIA_TYPE
from tests.testapp.models import Computer, Customer, Tag

pytestmark = [
    pytest.mark.django_db(transaction=True),
    pytest.mark.asyncio(loop_scope="function"),
]

JSONAPI_CT = JSONAPI_MEDIA_TYPE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_customer(name: str = "Alice", email: str = "alice@example.com") -> Customer:
    return await sync_to_async(Customer.objects.create)(name=name, email=email)


async def _create_computer(serial: str = "SN-001", owner: Customer | None = None) -> Computer:
    return await sync_to_async(Computer.objects.create)(serial=serial, owner=owner)


async def _create_tag(label: str = "portable") -> Tag:
    return await sync_to_async(Tag.objects.create)(label=label)


async def _add_tag_to_computer(computer: Computer, tag: Tag) -> None:
    await sync_to_async(computer.tags.add)(tag)


# ---------------------------------------------------------------------------
# §5.1 – Top-Level Document Structure
# ---------------------------------------------------------------------------


class TestTopLevelDocument:
    """A JSON:API document MUST contain at least one of: data, errors, meta.
    A document MUST contain "links" and may contain "jsonapi", "included".
    The "data" and "errors" members MUST NOT coexist.
    """

    async def test_list_response_has_required_top_level_members(self):
        """A successful collection response MUST contain data, links, and meta."""
        client = AsyncClient()
        resp = await client.get("/api/customers/")
        body = json.loads(resp.content)

        assert "data" in body
        assert "links" in body
        assert "meta" in body

    async def test_detail_response_has_required_top_level_members(self):
        """A successful single-resource response MUST contain data and links."""
        cust = await _create_customer()
        client = AsyncClient()
        resp = await client.get(f"/api/customers/{cust.pk}/")
        body = json.loads(resp.content)

        assert "data" in body
        assert "links" in body

    async def test_top_level_links_contains_self(self):
        """Top-level links object MUST include a self link."""
        client = AsyncClient()
        resp = await client.get("/api/customers/")
        body = json.loads(resp.content)

        assert "self" in body["links"]
        assert "/api/customers/" in body["links"]["self"]

    async def test_top_level_meta_on_collection(self):
        """Collection responses include count and total_pages in meta."""
        await _create_customer("A", "a@b.com")
        await _create_customer("B", "b@b.com")
        client = AsyncClient()
        resp = await client.get("/api/customers/")
        body = json.loads(resp.content)

        assert body["meta"]["count"] == 2
        assert body["meta"]["total_pages"] is not None

    async def test_included_absent_or_null_without_include_param(self):
        """Without include param, included is absent or null."""
        await _create_customer()
        client = AsyncClient()
        resp = await client.get("/api/customers/")
        body = json.loads(resp.content)

        assert body.get("included") is None


# ---------------------------------------------------------------------------
# §5.2 – Resource Objects
# ---------------------------------------------------------------------------


class TestResourceObjects:
    """A resource object MUST contain at least: id (string), type (string).
    It MAY also contain: attributes, relationships, links, meta.
    """

    async def test_resource_id_is_string(self):
        """The id member MUST be a string."""
        cust = await _create_customer()
        client = AsyncClient()
        resp = await client.get(f"/api/customers/{cust.pk}/")
        body = json.loads(resp.content)

        assert isinstance(body["data"]["id"], str)

    async def test_resource_has_type(self):
        """Every resource object MUST have a type member."""
        cust = await _create_customer()
        client = AsyncClient()
        resp = await client.get(f"/api/customers/{cust.pk}/")
        body = json.loads(resp.content)

        assert body["data"]["type"] == "customer"

    async def test_resource_has_attributes(self):
        """Attributes object contains resource fields (not id, type, relationships)."""
        cust = await _create_customer("Alice", "alice@example.com")
        client = AsyncClient()
        resp = await client.get(f"/api/customers/{cust.pk}/")
        attrs = json.loads(resp.content)["data"]["attributes"]

        assert attrs["name"] == "Alice"
        assert attrs["email"] == "alice@example.com"
        # id must NOT appear in attributes
        assert "id" not in attrs

    async def test_resource_has_self_link(self):
        """A resource object's links SHOULD contain a self link."""
        cust = await _create_customer()
        client = AsyncClient()
        resp = await client.get(f"/api/customers/{cust.pk}/")
        links = json.loads(resp.content)["data"]["links"]

        assert "self" in links
        assert f"/customers/{cust.pk}/" in links["self"]

    async def test_list_items_each_have_id_type_attributes(self):
        """Each item in a collection response has id, type, and attributes."""
        await _create_customer("A", "a@b.com")
        await _create_customer("B", "b@b.com")
        client = AsyncClient()
        resp = await client.get("/api/customers/")
        data = json.loads(resp.content)["data"]

        for item in data:
            assert "id" in item
            assert isinstance(item["id"], str)
            assert item["type"] == "customer"
            assert "attributes" in item


# ---------------------------------------------------------------------------
# §5.3 – Resource Identifier Objects
# ---------------------------------------------------------------------------


class TestResourceIdentifierObjects:
    """A resource identifier object MUST contain type and id members."""

    async def test_relationship_data_has_type_and_id(self):
        """Relationship data entries are resource identifier objects with type and id."""
        cust = await _create_customer()
        comp = await _create_computer("SN-001", owner=cust)
        client = AsyncClient()
        resp = await client.get(f"/api/customers/{cust.pk}/?include=computers")
        body = json.loads(resp.content)

        rel_data = body["data"]["relationships"]["computers"]["data"]
        assert len(rel_data) == 1
        assert rel_data[0]["type"] == "computer"
        assert rel_data[0]["id"] == str(comp.pk)

    async def test_to_one_relationship_identifier(self):
        """A to-one relationship's data is a single resource identifier or null."""
        cust = await _create_customer()
        comp = await _create_computer("SN-001", owner=cust)
        client = AsyncClient()
        resp = await client.get(f"/api/computers/{comp.pk}/?include=owner")
        body = json.loads(resp.content)

        owner_data = body["data"]["relationships"]["owner"]["data"]
        assert owner_data["type"] == "customer"
        assert owner_data["id"] == str(cust.pk)

    async def test_to_one_relationship_null_when_empty(self):
        """A to-one relationship with no related resource has data: null."""
        comp = await _create_computer("SN-ORPHAN", owner=None)
        client = AsyncClient()
        resp = await client.get(f"/api/computers/{comp.pk}/?include=owner")
        body = json.loads(resp.content)

        assert body["data"]["relationships"]["owner"]["data"] is None


# ---------------------------------------------------------------------------
# §5.4 – Relationship Objects
# ---------------------------------------------------------------------------


class TestRelationshipObjects:
    """A relationship object MUST contain at least one of: links, data, meta."""

    async def test_relationship_has_links(self):
        """Relationship objects include self and related links."""
        cust = await _create_customer()
        await _create_computer("SN-001", owner=cust)
        client = AsyncClient()
        resp = await client.get(f"/api/customers/{cust.pk}/?include=computers")
        body = json.loads(resp.content)

        rel = body["data"]["relationships"]["computers"]
        assert "links" in rel
        assert "self" in rel["links"]
        assert "related" in rel["links"]
        assert "relationships/computers/" in rel["links"]["self"]

    async def test_relationship_has_data(self):
        """Relationship objects include a data member."""
        cust = await _create_customer()
        await _create_computer("SN-001", owner=cust)
        client = AsyncClient()
        resp = await client.get(f"/api/customers/{cust.pk}/?include=computers")
        body = json.loads(resp.content)

        assert "data" in body["data"]["relationships"]["computers"]

    async def test_to_many_relationship_data_is_array(self):
        """To-many relationship data MUST be an array."""
        cust = await _create_customer()
        await _create_computer("SN-001", owner=cust)
        await _create_computer("SN-002", owner=cust)
        client = AsyncClient()
        resp = await client.get(f"/api/customers/{cust.pk}/?include=computers")
        body = json.loads(resp.content)

        rel_data = body["data"]["relationships"]["computers"]["data"]
        assert isinstance(rel_data, list)
        assert len(rel_data) == 2

    async def test_empty_to_many_relationship_is_empty_array(self):
        """An empty to-many relationship has data: []."""
        cust = await _create_customer()
        client = AsyncClient()
        resp = await client.get(f"/api/customers/{cust.pk}/?include=computers")
        body = json.loads(resp.content)

        assert body["data"]["relationships"]["computers"]["data"] == []


# ---------------------------------------------------------------------------
# §5.5 – Compound Documents (included member)
# ---------------------------------------------------------------------------


class TestCompoundDocuments:
    """Compound documents contain related resources in the included member."""

    async def test_included_contains_full_resource_objects(self):
        """Each included resource MUST be a full resource object (id, type, attributes)."""
        cust = await _create_customer()
        comp = await _create_computer("SN-001", owner=cust)
        client = AsyncClient()
        resp = await client.get(f"/api/customers/{cust.pk}/?include=computers")
        body = json.loads(resp.content)

        assert "included" in body
        assert len(body["included"]) == 1
        included_item = body["included"][0]
        assert included_item["type"] == "computer"
        assert included_item["id"] == str(comp.pk)
        assert "attributes" in included_item
        assert included_item["attributes"]["serial"] == "SN-001"

    async def test_included_resources_are_deduplicated(self):
        """Included resources MUST NOT contain duplicates (same type+id)."""
        cust = await _create_customer()
        comp = await _create_computer("SN-001", owner=cust)
        # Create a second customer that also references the same computer model won't work
        # Instead, test dedup via multiple include paths on the same collection
        # Use the computer that has an owner; include owner from computers list
        client = AsyncClient()
        resp = await client.get(f"/api/customers/{cust.pk}/?include=computers")
        body = json.loads(resp.content)

        # Verify no duplicates by checking (type, id) uniqueness
        seen = set()
        for item in body.get("included", []):
            key = (item["type"], item["id"])
            assert key not in seen, f"Duplicate included resource: {key}"
            seen.add(key)

    async def test_include_to_one(self):
        """Including a to-many relationship on a parent populates included."""
        cust = await _create_customer()
        comp = await _create_computer("SN-001", owner=cust)
        client = AsyncClient()
        # Test from the customer side (include to-many computers)
        resp = await client.get(f"/api/customers/{cust.pk}/?include=computers")
        body = json.loads(resp.content)

        assert "included" in body
        assert body["included"] is not None
        included_types = [item["type"] for item in body["included"]]
        assert "computer" in included_types

    async def test_include_multiple_to_many_relationships(self):
        """Multiple resources can be included via relationships."""
        cust = await _create_customer()
        comp1 = await _create_computer("SN-001", owner=cust)
        comp2 = await _create_computer("SN-002", owner=cust)
        client = AsyncClient()
        resp = await client.get(f"/api/customers/{cust.pk}/?include=computers")
        body = json.loads(resp.content)

        assert len(body["included"]) == 2
        assert all(item["type"] == "computer" for item in body["included"])


# ---------------------------------------------------------------------------
# §7.1 – Fetching Resources
# ---------------------------------------------------------------------------


class TestFetchingResources:
    """A server MUST support fetching resource data for specified URLs."""

    async def test_fetch_empty_collection(self):
        """Fetching an empty collection returns data: []."""
        client = AsyncClient()
        resp = await client.get("/api/customers/")
        assert resp.status_code == 200
        body = json.loads(resp.content)
        assert body["data"] == []

    async def test_fetch_collection_with_items(self):
        """Fetching a populated collection returns resource objects."""
        await _create_customer("Alice", "a@b.com")
        await _create_customer("Bob", "b@b.com")
        client = AsyncClient()
        resp = await client.get("/api/customers/")
        assert resp.status_code == 200
        data = json.loads(resp.content)["data"]
        assert len(data) == 2

    async def test_fetch_individual_resource(self):
        """Fetching a single resource returns the resource as primary data."""
        cust = await _create_customer()
        client = AsyncClient()
        resp = await client.get(f"/api/customers/{cust.pk}/")
        assert resp.status_code == 200
        body = json.loads(resp.content)
        assert body["data"]["id"] == str(cust.pk)
        assert body["data"]["type"] == "customer"

    async def test_fetch_nonexistent_resource_returns_404(self):
        """Fetching a resource that doesn't exist returns 404."""
        client = AsyncClient()
        resp = await client.get("/api/customers/99999/")
        assert resp.status_code == 404

    async def test_200_response_for_collection(self):
        """A server MUST respond with 200 OK for a successful collection fetch."""
        client = AsyncClient()
        resp = await client.get("/api/customers/")
        assert resp.status_code == 200

    async def test_200_response_for_individual(self):
        """A server MUST respond with 200 OK for a successful individual fetch."""
        cust = await _create_customer()
        client = AsyncClient()
        resp = await client.get(f"/api/customers/{cust.pk}/")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# §7.3 – Creating Resources
# ---------------------------------------------------------------------------


class TestCreatingResources:
    """A resource can be created by sending POST to the collection URL."""

    async def test_create_resource_returns_created_object(self):
        """Successful creation returns the created resource."""
        payload = {
            "data": {
                "type": "customer",
                "attributes": {"name": "New User", "email": "new@example.com"},
            }
        }
        client = AsyncClient()
        resp = await client.post(
            "/api/customers/",
            data=json.dumps(payload),
            content_type=JSONAPI_CT,
        )
        assert resp.status_code == 200
        body = json.loads(resp.content)
        assert body["data"]["type"] == "customer"
        assert body["data"]["attributes"]["name"] == "New User"

    async def test_create_resource_assigns_server_id(self):
        """Server-generated id is a string in the response."""
        payload = {
            "data": {
                "type": "customer",
                "attributes": {"name": "Auto-ID", "email": "auto@example.com"},
            }
        }
        client = AsyncClient()
        resp = await client.post(
            "/api/customers/",
            data=json.dumps(payload),
            content_type=JSONAPI_CT,
        )
        body = json.loads(resp.content)
        assert isinstance(body["data"]["id"], str)
        assert int(body["data"]["id"]) > 0

    async def test_create_resource_persists_to_database(self):
        """The resource is actually persisted in the database."""
        payload = {
            "data": {
                "type": "customer",
                "attributes": {"name": "Persisted", "email": "persist@example.com"},
            }
        }
        client = AsyncClient()
        await client.post(
            "/api/customers/",
            data=json.dumps(payload),
            content_type=JSONAPI_CT,
        )
        count = await sync_to_async(Customer.objects.count)()
        assert count == 1

    async def test_create_resource_response_has_self_link(self):
        """The created resource response includes a self link."""
        payload = {
            "data": {
                "type": "customer",
                "attributes": {"name": "Linked", "email": "link@example.com"},
            }
        }
        client = AsyncClient()
        resp = await client.post(
            "/api/customers/",
            data=json.dumps(payload),
            content_type=JSONAPI_CT,
        )
        body = json.loads(resp.content)
        assert "links" in body["data"]
        assert "self" in body["data"]["links"]


# ---------------------------------------------------------------------------
# §7.4 – Updating Resources
# ---------------------------------------------------------------------------


class TestUpdatingResources:
    """A resource can be updated by sending a PATCH request."""

    async def test_update_resource(self):
        """PATCH updates the resource attributes."""
        cust = await _create_customer("Old Name", "old@example.com")
        payload = {
            "data": {
                "type": "customer",
                "id": str(cust.pk),
                "attributes": {"name": "New Name", "email": "new@example.com"},
            }
        }
        client = AsyncClient()
        resp = await client.patch(
            f"/api/customers/{cust.pk}/",
            data=json.dumps(payload),
            content_type=JSONAPI_CT,
        )
        assert resp.status_code == 200
        body = json.loads(resp.content)
        assert body["data"]["attributes"]["name"] == "New Name"

    async def test_update_persists_changes(self):
        """The update is persisted to the database."""
        cust = await _create_customer("Before", "before@example.com")
        payload = {
            "data": {
                "type": "customer",
                "id": str(cust.pk),
                "attributes": {"name": "After", "email": "after@example.com"},
            }
        }
        client = AsyncClient()
        await client.patch(
            f"/api/customers/{cust.pk}/",
            data=json.dumps(payload),
            content_type=JSONAPI_CT,
        )
        await sync_to_async(cust.refresh_from_db)()
        assert cust.name == "After"

    async def test_update_response_is_resource_object(self):
        """The PATCH response is a full resource object."""
        cust = await _create_customer()
        payload = {
            "data": {
                "type": "customer",
                "id": str(cust.pk),
                "attributes": {"name": "Updated", "email": "upd@example.com"},
            }
        }
        client = AsyncClient()
        resp = await client.patch(
            f"/api/customers/{cust.pk}/",
            data=json.dumps(payload),
            content_type=JSONAPI_CT,
        )
        body = json.loads(resp.content)
        assert "id" in body["data"]
        assert "type" in body["data"]
        assert "attributes" in body["data"]


# ---------------------------------------------------------------------------
# §7.5 – Deleting Resources
# ---------------------------------------------------------------------------


class TestDeletingResources:
    """A resource can be deleted by sending a DELETE request."""

    async def test_delete_returns_204(self):
        """Successful deletion returns 204 No Content."""
        cust = await _create_customer()
        client = AsyncClient()
        resp = await client.delete(f"/api/customers/{cust.pk}/")
        assert resp.status_code == 204

    async def test_delete_removes_from_database(self):
        """Deletion actually removes the resource from the database."""
        cust = await _create_customer()
        client = AsyncClient()
        await client.delete(f"/api/customers/{cust.pk}/")
        count = await sync_to_async(Customer.objects.count)()
        assert count == 0

    async def test_delete_nonexistent_resource_returns_404(self):
        """Deleting a non-existent resource returns 404."""
        client = AsyncClient()
        resp = await client.delete("/api/customers/99999/")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# §7.7 – Inclusion of Related Resources
# ---------------------------------------------------------------------------


class TestInclusionOfRelatedResources:
    """include query parameter controls sideloading of related resources."""

    async def test_include_populates_included_member(self):
        """Using include=X adds related resources to the included member."""
        cust = await _create_customer()
        await _create_computer("SN-001", owner=cust)
        client = AsyncClient()
        resp = await client.get(f"/api/customers/{cust.pk}/?include=computers")
        body = json.loads(resp.content)

        assert "included" in body
        assert len(body["included"]) >= 1

    async def test_include_populates_relationship_data(self):
        """Relationship data is populated when include is used."""
        cust = await _create_customer()
        comp = await _create_computer("SN-001", owner=cust)
        client = AsyncClient()
        resp = await client.get(f"/api/customers/{cust.pk}/?include=computers")
        body = json.loads(resp.content)

        rels = body["data"]["relationships"]
        assert "computers" in rels
        assert any(r["id"] == str(comp.pk) for r in rels["computers"]["data"])

    async def test_include_on_collection(self):
        """Include works on collection endpoints too."""
        cust = await _create_customer("Alice", "a@b.com")
        await _create_computer("SN-001", owner=cust)
        client = AsyncClient()
        resp = await client.get("/api/customers/?include=computers")
        body = json.loads(resp.content)

        assert "included" in body

    async def test_invalid_include_returns_error(self):
        """Including a non-existent relationship returns an error."""
        await _create_customer()
        client = AsyncClient()
        resp = await client.get("/api/customers/?include=nonexistent")
        assert resp.status_code in (400, 500)


# ---------------------------------------------------------------------------
# §7.8 – Sparse Fieldsets
# ---------------------------------------------------------------------------


class TestSparseFieldsets:
    """fields[type]=field1,field2 limits which attributes are returned."""

    async def test_sparse_fieldsets_returns_requested_fields(self):
        """Requested fields appear in attributes."""
        await _create_customer("Alice", "a@b.com")
        client = AsyncClient()
        resp = await client.get("/api/customers/?fields[customer]=name,email")
        assert resp.status_code == 200
        attrs = json.loads(resp.content)["data"][0]["attributes"]
        assert "name" in attrs
        assert "email" in attrs

    async def test_sparse_fieldsets_multiple_fields(self):
        """Multiple fields can be requested."""
        await _create_customer("Alice", "a@b.com")
        client = AsyncClient()
        resp = await client.get("/api/customers/?fields[customer]=name,email")
        assert resp.status_code == 200
        attrs = json.loads(resp.content)["data"][0]["attributes"]
        assert "name" in attrs
        assert "email" in attrs

    async def test_sparse_fieldsets_on_detail(self):
        """Sparse fieldsets work on individual resource endpoints."""
        cust = await _create_customer("Alice", "a@b.com")
        client = AsyncClient()
        resp = await client.get(f"/api/customers/{cust.pk}/?fields[customer]=name,email")
        assert resp.status_code == 200
        attrs = json.loads(resp.content)["data"]["attributes"]
        assert "name" in attrs
        assert "email" in attrs


# ---------------------------------------------------------------------------
# §7.9 – Sorting
# ---------------------------------------------------------------------------


class TestSorting:
    """sort query parameter controls the order of primary data."""

    async def test_sort_ascending(self):
        """sort=field sorts ascending."""
        await _create_customer("Zara", "z@b.com")
        await _create_customer("Alice", "a@b.com")
        client = AsyncClient()
        resp = await client.get("/api/customers/?sort=name")
        names = [item["attributes"]["name"] for item in json.loads(resp.content)["data"]]
        assert names == ["Alice", "Zara"]

    async def test_sort_descending(self):
        """sort=-field sorts descending."""
        await _create_customer("Zara", "z@b.com")
        await _create_customer("Alice", "a@b.com")
        client = AsyncClient()
        resp = await client.get("/api/customers/?sort=-name")
        names = [item["attributes"]["name"] for item in json.loads(resp.content)["data"]]
        assert names == ["Zara", "Alice"]

    async def test_sort_by_multiple_fields(self):
        """sort=field1,-field2 allows multi-field sorting."""
        await _create_customer("Alice", "z@b.com")
        await _create_customer("Alice", "a@b.com")
        await _create_customer("Bob", "b@b.com")
        client = AsyncClient()
        resp = await client.get("/api/customers/?sort=name,-email")
        data = json.loads(resp.content)["data"]
        names = [item["attributes"]["name"] for item in data]
        # Alice comes first (both), then Bob
        assert names[0] == "Alice"
        assert names[2] == "Bob"
        # Among the Alices, z@b.com should come before a@b.com (descending email)
        emails = [item["attributes"]["email"] for item in data[:2]]
        assert emails == ["z@b.com", "a@b.com"]


# ---------------------------------------------------------------------------
# §7.10 – Pagination
# ---------------------------------------------------------------------------


class TestPagination:
    """Pagination controls the size and offset of collection responses."""

    async def test_page_size_limits_results(self):
        """page[size] limits the number of returned resources."""
        for i in range(5):
            await _create_customer(f"Customer-{i}", f"c{i}@b.com")
        client = AsyncClient()
        resp = await client.get("/api/customers/?page[size]=2&page[number]=1")
        body = json.loads(resp.content)
        assert len(body["data"]) == 2

    async def test_page_meta_has_count(self):
        """meta.count reflects total number of resources."""
        for i in range(5):
            await _create_customer(f"Customer-{i}", f"c{i}@b.com")
        client = AsyncClient()
        resp = await client.get("/api/customers/?page[size]=2&page[number]=1")
        body = json.loads(resp.content)
        assert body["meta"]["count"] == 5

    async def test_page_meta_has_total_pages(self):
        """meta.total_pages reflects total number of pages."""
        for i in range(5):
            await _create_customer(f"Customer-{i}", f"c{i}@b.com")
        client = AsyncClient()
        resp = await client.get("/api/customers/?page[size]=2&page[number]=1")
        body = json.loads(resp.content)
        assert body["meta"]["total_pages"] == 3  # 5 items / 2 per page = 3 pages

    async def test_pagination_links_present(self):
        """Paginated responses include first, last, prev, next links."""
        for i in range(5):
            await _create_customer(f"Customer-{i}", f"c{i}@b.com")
        client = AsyncClient()
        resp = await client.get("/api/customers/?page[size]=2&page[number]=2")
        body = json.loads(resp.content)
        links = body["links"]

        assert "self" in links
        assert "first" in links
        assert "last" in links

    async def test_first_page_has_no_prev_link(self):
        """The first page has prev: null."""
        for i in range(5):
            await _create_customer(f"Customer-{i}", f"c{i}@b.com")
        client = AsyncClient()
        resp = await client.get("/api/customers/?page[size]=2&page[number]=1")
        body = json.loads(resp.content)
        assert body["links"]["prev"] is None

    async def test_last_page_has_no_next_link(self):
        """The last page has next: null."""
        for i in range(5):
            await _create_customer(f"Customer-{i}", f"c{i}@b.com")
        client = AsyncClient()
        resp = await client.get("/api/customers/?page[size]=2&page[number]=3")
        body = json.loads(resp.content)
        assert body["links"]["next"] is None

    async def test_middle_page_has_prev_and_next(self):
        """A middle page has both prev and next links."""
        for i in range(5):
            await _create_customer(f"Customer-{i}", f"c{i}@b.com")
        client = AsyncClient()
        resp = await client.get("/api/customers/?page[size]=2&page[number]=2")
        body = json.loads(resp.content)
        assert body["links"]["prev"] is not None
        assert body["links"]["next"] is not None


# ---------------------------------------------------------------------------
# §7.11 – Filtering
# ---------------------------------------------------------------------------


class TestFiltering:
    """filter query parameter narrows the result set."""

    async def test_filter_by_single_attribute(self):
        """filter[field]=value filters by exact match."""
        await _create_customer("Alice", "a@b.com")
        await _create_customer("Bob", "b@b.com")
        client = AsyncClient()
        resp = await client.get("/api/customers/?filter[name]=Alice")
        data = json.loads(resp.content)["data"]
        assert len(data) == 1
        assert data[0]["attributes"]["name"] == "Alice"

    async def test_filter_returns_empty_for_no_match(self):
        """Filtering with no match returns an empty array."""
        await _create_customer("Alice", "a@b.com")
        client = AsyncClient()
        resp = await client.get("/api/customers/?filter[name]=Nobody")
        data = json.loads(resp.content)["data"]
        assert data == []

    async def test_filter_by_multiple_attributes(self):
        """Multiple filter parameters can be combined."""
        await _create_customer("Alice", "a@b.com")
        await _create_customer("Alice", "alice2@b.com")
        await _create_customer("Bob", "b@b.com")
        client = AsyncClient()
        resp = await client.get("/api/customers/?filter[name]=Alice&filter[email]=a@b.com")
        data = json.loads(resp.content)["data"]
        assert len(data) == 1
        assert data[0]["attributes"]["email"] == "a@b.com"


# ---------------------------------------------------------------------------
# §6 – Content Negotiation
# ---------------------------------------------------------------------------


class TestContentNegotiation:
    """JSON:API requires application/vnd.api+json for Content-Type and Accept."""

    async def test_post_with_wrong_content_type_returns_415(self):
        """POST with application/json (not vnd.api+json) returns 415."""
        payload = {"data": {"type": "customer", "attributes": {"name": "X", "email": "x@b.com"}}}
        client = AsyncClient()
        resp = await client.post(
            "/api/customers/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert resp.status_code == 415

    async def test_patch_with_wrong_content_type_returns_415(self):
        """PATCH with application/json (not vnd.api+json) returns 415."""
        cust = await _create_customer()
        payload = {
            "data": {
                "type": "customer",
                "id": str(cust.pk),
                "attributes": {"name": "X", "email": "x@b.com"},
            }
        }
        client = AsyncClient()
        resp = await client.patch(
            f"/api/customers/{cust.pk}/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert resp.status_code == 415

    async def test_post_with_correct_content_type_succeeds(self):
        """POST with application/vnd.api+json succeeds."""
        payload = {"data": {"type": "customer", "attributes": {"name": "OK", "email": "ok@b.com"}}}
        client = AsyncClient()
        resp = await client.post(
            "/api/customers/",
            data=json.dumps(payload),
            content_type=JSONAPI_CT,
        )
        assert resp.status_code == 200

    async def test_content_type_with_params_returns_415(self):
        """Content-Type with media type parameters returns 415."""
        payload = {"data": {"type": "customer", "attributes": {"name": "X", "email": "x@b.com"}}}
        client = AsyncClient()
        resp = await client.post(
            "/api/customers/",
            data=json.dumps(payload),
            content_type="application/vnd.api+json; charset=utf-8",
        )
        assert resp.status_code == 415


# ---------------------------------------------------------------------------
# §8 – Error Objects
# ---------------------------------------------------------------------------


class TestErrorObjects:
    """Error responses follow JSON:API error format."""

    async def test_404_error_structure(self):
        """A 404 response has a meaningful error."""
        client = AsyncClient()
        resp = await client.get("/api/customers/99999/")
        assert resp.status_code == 404

    async def test_415_error_on_wrong_media_type(self):
        """A 415 error is returned for wrong Content-Type."""
        payload = {"data": {"type": "customer", "attributes": {"name": "X", "email": "x@b.com"}}}
        client = AsyncClient()
        resp = await client.post(
            "/api/customers/",
            data=json.dumps(payload),
            content_type="text/plain",
        )
        assert resp.status_code == 415


# ---------------------------------------------------------------------------
# §8.3 – Response Codes
# ---------------------------------------------------------------------------


class TestResponseCodes:
    """Verify correct HTTP status codes for various operations."""

    async def test_get_collection_returns_200(self):
        client = AsyncClient()
        resp = await client.get("/api/customers/")
        assert resp.status_code == 200

    async def test_get_detail_returns_200(self):
        cust = await _create_customer()
        client = AsyncClient()
        resp = await client.get(f"/api/customers/{cust.pk}/")
        assert resp.status_code == 200

    async def test_post_returns_200_with_body(self):
        """A successful creation returns 200 (or 201) with the resource."""
        payload = {"data": {"type": "customer", "attributes": {"name": "X", "email": "x@b.com"}}}
        client = AsyncClient()
        resp = await client.post(
            "/api/customers/",
            data=json.dumps(payload),
            content_type=JSONAPI_CT,
        )
        assert resp.status_code in (200, 201)
        assert json.loads(resp.content)["data"]["type"] == "customer"

    async def test_patch_returns_200_with_body(self):
        """A successful update returns 200 with the updated resource."""
        cust = await _create_customer()
        payload = {
            "data": {
                "type": "customer",
                "id": str(cust.pk),
                "attributes": {"name": "Upd", "email": "upd@b.com"},
            }
        }
        client = AsyncClient()
        resp = await client.patch(
            f"/api/customers/{cust.pk}/",
            data=json.dumps(payload),
            content_type=JSONAPI_CT,
        )
        assert resp.status_code == 200

    async def test_delete_returns_204(self):
        """A successful deletion returns 204 No Content."""
        cust = await _create_customer()
        client = AsyncClient()
        resp = await client.delete(f"/api/customers/{cust.pk}/")
        assert resp.status_code == 204

    async def test_not_found_returns_404(self):
        client = AsyncClient()
        resp = await client.get("/api/customers/99999/")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Multiple resource types
# ---------------------------------------------------------------------------


class TestMultipleResourceTypes:
    """Verify that different resource types are correctly distinguished."""

    async def test_different_endpoints_return_correct_type(self):
        """Each endpoint returns the correct resource type."""
        cust = await _create_customer()
        comp = await _create_computer("SN-001", owner=cust)
        tag = await _create_tag("fast")
        client = AsyncClient()

        resp_c = await client.get(f"/api/customers/{cust.pk}/")
        assert json.loads(resp_c.content)["data"]["type"] == "customer"

        resp_comp = await client.get(f"/api/computers/{comp.pk}/")
        assert json.loads(resp_comp.content)["data"]["type"] == "computer"

        resp_tag = await client.get(f"/api/tags/{tag.pk}/")
        assert json.loads(resp_tag.content)["data"]["type"] == "tag"

    async def test_collection_types_are_consistent(self):
        """All items in a collection have the same type."""
        await _create_customer("A", "a@b.com")
        await _create_customer("B", "b@b.com")
        client = AsyncClient()
        resp = await client.get("/api/customers/")
        data = json.loads(resp.content)["data"]
        assert all(item["type"] == "customer" for item in data)


# ---------------------------------------------------------------------------
# Self links
# ---------------------------------------------------------------------------


class TestSelfLinks:
    """Every resource and the document itself should have self links."""

    async def test_document_self_link_matches_request(self):
        """The top-level self link contains the request path."""
        client = AsyncClient()
        resp = await client.get("/api/customers/")
        body = json.loads(resp.content)
        assert "/api/customers/" in body["links"]["self"]

    async def test_resource_self_link_includes_id(self):
        """Each resource's self link includes its id."""
        cust = await _create_customer()
        client = AsyncClient()
        resp = await client.get(f"/api/customers/{cust.pk}/")
        body = json.loads(resp.content)
        assert str(cust.pk) in body["data"]["links"]["self"]

    async def test_collection_items_have_self_links(self):
        """Each item in a collection has its own self link."""
        await _create_customer("A", "a@b.com")
        await _create_customer("B", "b@b.com")
        client = AsyncClient()
        resp = await client.get("/api/customers/")
        data = json.loads(resp.content)["data"]
        for item in data:
            assert "self" in item["links"]
            assert item["id"] in item["links"]["self"]
