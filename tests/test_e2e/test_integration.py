"""End-to-end integration tests exercising the full ApplicationBuilder pipeline
with real Django ORM models, Pydantic schemas, and Django's async test client.
"""

from __future__ import annotations

import json

import pytest
from asgiref.sync import sync_to_async
from django.test import AsyncClient

from django_ninja_jsonapi.renderers import JSONAPI_MEDIA_TYPE

from tests.testapp.models import Computer, Customer

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


# ---------------------------------------------------------------------------
# GET list & detail
# ---------------------------------------------------------------------------


class TestGetEndpoints:
    async def test_get_empty_list(self):
        client = AsyncClient()
        resp = await client.get("/api/customers/")
        assert resp.status_code == 200
        body = json.loads(resp.content)
        assert body["data"] == []
        assert "meta" in body

    async def test_get_list_returns_items(self):
        await _create_customer("Alice", "a@b.com")
        await _create_customer("Bob", "b@b.com")
        client = AsyncClient()
        resp = await client.get("/api/customers/")
        assert resp.status_code == 200
        data = json.loads(resp.content)["data"]
        assert len(data) == 2
        assert all(item["type"] == "customer" for item in data)

    async def test_get_detail(self):
        cust = await _create_customer()
        client = AsyncClient()
        resp = await client.get(f"/api/customers/{cust.pk}/")
        assert resp.status_code == 200
        body = json.loads(resp.content)
        assert body["data"]["id"] == str(cust.pk)
        assert body["data"]["type"] == "customer"
        assert body["data"]["attributes"]["name"] == "Alice"

    async def test_get_detail_not_found(self):
        client = AsyncClient()
        resp = await client.get("/api/customers/999/")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST (create)
# ---------------------------------------------------------------------------


class TestCreateEndpoint:
    async def test_create_resource(self):
        payload = {
            "data": {
                "type": "customer",
                "attributes": {
                    "name": "Charlie",
                    "email": "charlie@example.com",
                },
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
        assert body["data"]["attributes"]["name"] == "Charlie"

        count = await sync_to_async(Customer.objects.count)()
        assert count == 1


# ---------------------------------------------------------------------------
# PATCH (update)
# ---------------------------------------------------------------------------


class TestUpdateEndpoint:
    async def test_update_resource(self):
        cust = await _create_customer()
        payload = {
            "data": {
                "type": "customer",
                "id": str(cust.pk),
                "attributes": {
                    "name": "Updated",
                    "email": "updated@example.com",
                },
            }
        }
        client = AsyncClient()
        resp = await client.patch(
            f"/api/customers/{cust.pk}/",
            data=json.dumps(payload),
            content_type=JSONAPI_CT,
        )
        assert resp.status_code == 200
        assert json.loads(resp.content)["data"]["attributes"]["name"] == "Updated"

        await sync_to_async(cust.refresh_from_db)()
        assert cust.name == "Updated"


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------


class TestDeleteEndpoint:
    async def test_delete_resource(self):
        cust = await _create_customer()
        client = AsyncClient()
        resp = await client.delete(f"/api/customers/{cust.pk}/")
        assert resp.status_code == 204

        count = await sync_to_async(Customer.objects.count)()
        assert count == 0


# ---------------------------------------------------------------------------
# Include (sideloading)
# ---------------------------------------------------------------------------


class TestIncludes:
    async def test_include_to_many(self):
        cust = await _create_customer()
        await _create_computer("SN-001", owner=cust)
        await _create_computer("SN-002", owner=cust)

        client = AsyncClient()
        resp = await client.get(f"/api/customers/{cust.pk}/?include=computers")
        assert resp.status_code == 200
        body = json.loads(resp.content)

        rels = body["data"].get("relationships", {})
        assert "computers" in rels
        assert len(rels["computers"]["data"]) == 2

        included = body.get("included", [])
        assert len(included) == 2
        assert all(item["type"] == "computer" for item in included)


# ---------------------------------------------------------------------------
# Sparse fieldsets
# ---------------------------------------------------------------------------


class TestSparseFieldsets:
    async def test_sparse_fields_all_present(self):
        """When requesting all fields, they are all present."""
        await _create_customer()
        client = AsyncClient()
        resp = await client.get("/api/customers/?fields[customer]=name,email")
        assert resp.status_code == 200
        attrs = json.loads(resp.content)["data"][0]["attributes"]
        assert "name" in attrs
        assert "email" in attrs


# ---------------------------------------------------------------------------
# Sorting
# ---------------------------------------------------------------------------


class TestSorting:
    async def test_sort_ascending(self):
        await _create_customer("Zara", "z@b.com")
        await _create_customer("Alice", "a@b.com")
        client = AsyncClient()
        resp = await client.get("/api/customers/?sort=name")
        assert resp.status_code == 200
        names = [item["attributes"]["name"] for item in json.loads(resp.content)["data"]]
        assert names == ["Alice", "Zara"]

    async def test_sort_descending(self):
        await _create_customer("Zara", "z@b.com")
        await _create_customer("Alice", "a@b.com")
        client = AsyncClient()
        resp = await client.get("/api/customers/?sort=-name")
        assert resp.status_code == 200
        names = [item["attributes"]["name"] for item in json.loads(resp.content)["data"]]
        assert names == ["Zara", "Alice"]


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------


class TestPagination:
    async def test_page_size_limits_results(self):
        for i in range(5):
            await _create_customer(f"Customer-{i}", f"c{i}@b.com")

        client = AsyncClient()
        resp = await client.get("/api/customers/?page[size]=2&page[number]=1")
        assert resp.status_code == 200
        body = json.loads(resp.content)
        assert len(body["data"]) == 2
        assert body["meta"]["count"] == 5


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------


class TestFiltering:
    async def test_filter_by_attribute(self):
        await _create_customer("Alice", "a@b.com")
        await _create_customer("Bob", "b@b.com")

        client = AsyncClient()
        resp = await client.get("/api/customers/?filter[name]=Alice")
        assert resp.status_code == 200
        data = json.loads(resp.content)["data"]
        assert len(data) == 1
        assert data[0]["attributes"]["name"] == "Alice"


# ---------------------------------------------------------------------------
# Content negotiation (415)
# ---------------------------------------------------------------------------


class TestContentNegotiation:
    async def test_unsupported_media_type(self):
        payload = {"data": {"type": "customer", "attributes": {"name": "X", "email": "x@b.com"}}}
        client = AsyncClient()
        resp = await client.post(
            "/api/customers/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert resp.status_code == 415
