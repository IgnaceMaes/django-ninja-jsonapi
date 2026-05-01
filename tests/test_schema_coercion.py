"""Tests for schema-aware model coercion in the renderer."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

from django.db import models as django_models
from django.test import RequestFactory
from pydantic import BaseModel, ConfigDict

from django_ninja_jsonapi.renderers import (
    REQUEST_JSONAPI_CONFIG_ATTR,
    JSONAPIRenderer,
    JSONAPIResourceConfig,
)


class ArticleSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    computed_field: str | None = None


def _make_fake_django_model(fields_dict, *, properties=None):
    """Build a minimal Django model mock with optional @property-like attributes."""
    meta_fields = []

    for name in fields_dict:
        field = SimpleNamespace(name=name, attname=name)
        meta_fields.append(field)

    meta = SimpleNamespace(get_fields=lambda: meta_fields)

    obj = MagicMock(spec=django_models.Model)
    obj._meta = meta

    for name, value in fields_dict.items():
        setattr(obj, name, value)

    # Set property-like attributes
    if properties:
        for name, value in properties.items():
            setattr(obj, name, value)

    return obj


def _render_payload(request, data):
    payload = JSONAPIRenderer().render(request, data, response_status=200)
    if isinstance(payload, bytes):
        return json.loads(payload.decode())
    return json.loads(payload)


class TestSchemaAwareCoercion:
    def test_coerce_with_schema_includes_property_fields(self):
        """When a schema is provided, @property fields should be included."""
        obj = _make_fake_django_model(
            {"id": 1, "title": "Hello"},
            properties={"computed_field": "computed_value"},
        )

        result = JSONAPIRenderer._coerce_to_dict(obj, schema=ArticleSchema)

        assert result["id"] == 1
        assert result["title"] == "Hello"
        assert result["computed_field"] == "computed_value"

    def test_coerce_without_schema_misses_properties(self):
        """Without a schema, only DB fields are extracted."""
        obj = _make_fake_django_model(
            {"id": 1, "title": "Hello"},
            properties={"computed_field": "computed_value"},
        )

        result = JSONAPIRenderer._coerce_to_dict(obj)

        assert result["id"] == 1
        assert result["title"] == "Hello"
        assert "computed_field" not in result

    def test_renderer_uses_schema_from_resource_config(self):
        """End-to-end: renderer should use the schema from JSONAPIResourceConfig."""
        obj = _make_fake_django_model(
            {"id": 1, "title": "Hello"},
            properties={"computed_field": "computed_value"},
        )

        request = RequestFactory().get("/articles/1/")
        setattr(
            request,
            REQUEST_JSONAPI_CONFIG_ATTR,
            JSONAPIResourceConfig(resource_type="articles", schema=ArticleSchema),
        )

        result = _render_payload(request, obj)

        assert result["data"]["id"] == "1"
        assert result["data"]["attributes"]["title"] == "Hello"
        assert result["data"]["attributes"]["computed_field"] == "computed_value"

    def test_renderer_without_schema_fallback(self):
        """Without a schema, renderer should still work with DB fields only."""
        obj = _make_fake_django_model({"id": 1, "title": "Hello"})

        request = RequestFactory().get("/articles/1/")
        setattr(
            request,
            REQUEST_JSONAPI_CONFIG_ATTR,
            JSONAPIResourceConfig(resource_type="articles"),
        )

        result = _render_payload(request, obj)

        assert result["data"]["id"] == "1"
        assert result["data"]["attributes"]["title"] == "Hello"
