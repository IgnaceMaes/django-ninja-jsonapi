"""Tests for JsonApiResource config holder."""

import pytest
from pydantic import BaseModel

from django_ninja_jsonapi.resource import JsonApiResource
from django_ninja_jsonapi.schema_factory import JsonApiBody


class ArticleSchema(BaseModel):
    id: int
    title: str
    body: str
    author: dict | None = None


class ArticleCreateSchema(BaseModel):
    title: str
    body: str


class ArticleUpdateSchema(BaseModel):
    title: str | None = None
    body: str | None = None


class TestJsonApiResource:
    def _make_resource(self, **kwargs) -> JsonApiResource:
        defaults = {
            "resource_type": "articles",
            "id_field": "uuid",
            "schema": ArticleSchema,
            "schema_create": ArticleCreateSchema,
            "schema_update": ArticleUpdateSchema,
            "relationships": {
                "author": {"resource_type": "people"},
            },
        }
        defaults.update(kwargs)
        return JsonApiResource(**defaults)  # ty: ignore[invalid-argument-type]

    # ----- response() -----

    def test_response_detail(self):
        resource = self._make_resource()
        model = resource.response()
        assert "data" in model.model_fields

    def test_response_list(self):
        resource = self._make_resource()
        model = resource.response(many=True)
        data_field = model.model_fields["data"]
        assert hasattr(data_field.annotation, "__origin__") and data_field.annotation.__origin__ is list

    def test_response_without_schema_raises(self):
        resource = JsonApiResource(resource_type="articles")
        with pytest.raises(ValueError, match="requires 'schema'"):
            resource.response()

    # ----- body() / body_create() / body_update() -----

    def test_body_create(self):
        resource = self._make_resource()
        model = resource.body_create()
        assert "data" in model.model_fields

        # Should use ArticleCreateSchema
        parsed = model.model_validate(
            {
                "data": {
                    "type": "articles",
                    "attributes": {"title": "Hello", "body": "World"},
                }
            }
        )
        assert parsed.data.attributes.title == "Hello"  # ty: ignore[unresolved-attribute]

    def test_body_update(self):
        resource = self._make_resource()
        model = resource.body_update()
        assert "data" in model.model_fields

        # Should use ArticleUpdateSchema (all optional)
        parsed = model.model_validate(
            {
                "data": {
                    "type": "articles",
                    "attributes": {"title": "Updated"},
                }
            }
        )
        assert parsed.data.attributes.title == "Updated"  # ty: ignore[unresolved-attribute]

    def test_body_with_allow_id(self):
        resource = self._make_resource()
        model = resource.body_create(allow_id=True)
        data_type = model.model_fields["data"].annotation
        assert "id" in data_type.model_fields

    def test_body_without_schemas_raises(self):
        resource = JsonApiResource(resource_type="articles")
        with pytest.raises(ValueError, match="requires"):
            resource.body()

    def test_body_includes_relationships(self):
        resource = self._make_resource()
        model = resource.body_create()
        data_type = model.model_fields["data"].annotation
        assert "relationships" in data_type.model_fields

    # ----- decorator() -----

    def test_decorator_returns_callable(self):
        resource = self._make_resource()
        dec = resource.decorator()
        assert callable(dec)

    def test_decorator_applies_to_function(self):
        from django.test import RequestFactory

        from django_ninja_jsonapi.renderers import REQUEST_JSONAPI_CONFIG_ATTR

        resource = self._make_resource()

        @resource.decorator()
        def my_endpoint(request):
            return {"id": 1, "title": "Hello"}

        request = RequestFactory().get("/articles/1/")
        my_endpoint(request)

        config = getattr(request, REQUEST_JSONAPI_CONFIG_ATTR)
        assert config.resource_type == "articles"
        assert config.id_field == "uuid"
        assert "author" in config.relationships

    def test_decorator_with_overrides(self):
        from django.test import RequestFactory

        from django_ninja_jsonapi.renderers import REQUEST_JSONAPI_CONFIG_ATTR

        resource = self._make_resource()

        @resource.decorator(include_jsonapi_object=True)
        def my_endpoint(request):
            return {"id": 1, "title": "Hello"}

        request = RequestFactory().get("/articles/1/")
        my_endpoint(request)

        config = getattr(request, REQUEST_JSONAPI_CONFIG_ATTR)
        assert config.include_jsonapi_object is True

    # ----- body models are generic -----

    def test_body_is_subclass_of_JsonApiBody(self):
        resource = self._make_resource()
        model = resource.body_create()
        assert issubclass(model, JsonApiBody)
