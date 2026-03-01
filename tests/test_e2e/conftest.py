"""Conftest for E2E integration tests.

Builds the ApplicationBuilder-based API inside a per-test fixture so that
the global storages are populated *after* the snapshot is taken by
``reset_global_storages`` (from the root conftest), preventing leakage into
unit tests.
"""

from __future__ import annotations

import sys
import types
from typing import Annotated, Optional

import pytest
from django.urls import path
from ninja import NinjaAPI
from pydantic import BaseModel

from django_ninja_jsonapi.api.application_builder import ApplicationBuilder
from django_ninja_jsonapi.generics import ViewBaseGeneric
from django_ninja_jsonapi.types_metadata import RelationshipInfo

from tests.testapp.models import Computer, Customer, Tag


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class TagSchema(BaseModel):
    id: int
    label: str
    model_config = {"from_attributes": True}


class CustomerSchema(BaseModel):
    id: int
    name: str
    email: str
    computers: Annotated[
        list["ComputerSchema"],
        RelationshipInfo(resource_type="computer", many=True),
    ] = []
    model_config = {"from_attributes": True}


class ComputerSchema(BaseModel):
    id: int
    serial: str
    owner: Annotated[
        Optional["CustomerSchema"],
        RelationshipInfo(resource_type="customer", many=False),
    ] = None
    tags: Annotated[
        list[TagSchema],
        RelationshipInfo(resource_type="tag", many=True),
    ] = []
    model_config = {"from_attributes": True}


CustomerSchema.model_rebuild()
ComputerSchema.model_rebuild()


class ComputerCreateSchema(BaseModel):
    serial: str


class CustomerCreateSchema(BaseModel):
    name: str
    email: str


class GenericView(ViewBaseGeneric):
    pass


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_NS = "e2e-integration"


@pytest.fixture(autouse=True)
def e2e_api(settings):
    """Build the API, register URL patterns, and tear down after the test."""
    # Ensure the namespace is not already registered (cleanup from prior test).
    while _NS in NinjaAPI._registry:
        NinjaAPI._registry.remove(_NS)

    api = NinjaAPI(urls_namespace=_NS)
    builder = ApplicationBuilder(api)

    builder.add_resource(
        path="/customers",
        tags=["customers"],
        resource_type="customer",
        view=GenericView,
        model=Customer,
        schema=CustomerSchema,
        schema_in_post=CustomerCreateSchema,
        schema_in_patch=CustomerCreateSchema,
    )
    builder.add_resource(
        path="/computers",
        tags=["computers"],
        resource_type="computer",
        view=GenericView,
        model=Computer,
        schema=ComputerSchema,
        schema_in_post=ComputerCreateSchema,
        schema_in_patch=ComputerCreateSchema,
    )
    builder.add_resource(
        path="/tags",
        tags=["tags"],
        resource_type="tag",
        view=GenericView,
        model=Tag,
        schema=TagSchema,
    )
    builder.initialize()

    # Create a proper URL module and register it in sys.modules so Django's
    # URL resolver can import it.
    url_module = types.ModuleType("_e2e_urls")
    url_module.urlpatterns = [path("api/", api.urls)]
    sys.modules["_e2e_urls"] = url_module
    settings.ROOT_URLCONF = "_e2e_urls"

    yield api

    # Cleanup
    sys.modules.pop("_e2e_urls", None)
    while _NS in NinjaAPI._registry:
        NinjaAPI._registry.remove(_NS)
