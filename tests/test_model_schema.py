"""Tests for ModelSchema base class."""

import uuid
from typing import Any

import pytest
from django.db import models

from django_ninja_jsonapi._model_schema import ModelSchema

# ---------------------------------------------------------------------------
# Test Django models
# ---------------------------------------------------------------------------


class Organization(models.Model):
    name = models.CharField(max_length=200)

    class Meta:
        app_label = "testapp"


class Article(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True)
    title = models.CharField(max_length=200)
    body = models.TextField()
    status = models.CharField(max_length=20, default="draft")
    is_active = models.BooleanField(default=True)
    created_dt = models.DateTimeField(auto_now_add=True)
    updated_dt = models.DateTimeField(auto_now=True)
    view_count = models.IntegerField(default=0)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True)

    @property
    def organization_name(self) -> str:
        if self.organization:
            return str(self.organization.name)
        return ""

    class Meta:
        app_label = "testapp"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# ModelSchema (class-based)
# ---------------------------------------------------------------------------


class TestModelSchemaClassBasic:
    def test_generates_fields_from_meta(self):
        class ArticleOut(ModelSchema):
            class Meta:
                model = Article
                fields = ["title", "body"]

        assert "title" in ArticleOut.model_fields
        assert "body" in ArticleOut.model_fields
        assert "status" not in ArticleOut.model_fields

    def test_from_attributes_config(self):
        class ArticleOut(ModelSchema):
            class Meta:
                model = Article
                fields = ["title"]

        assert ArticleOut.model_config.get("from_attributes") is True

    def test_class_name_preserved(self):
        class MyArticle(ModelSchema):
            class Meta:
                model = Article
                fields = ["title"]

        assert MyArticle.__name__ == "MyArticle"

    def test_all_fields_when_none(self):
        class ArticleOut(ModelSchema):
            class Meta:
                model = Article

        assert "title" in ArticleOut.model_fields
        assert "body" in ArticleOut.model_fields

    def test_exclude_fields(self):
        class ArticleOut(ModelSchema):
            class Meta:
                model = Article
                fields = ["title", "body", "status"]
                exclude = {"status"}

        assert "title" in ArticleOut.model_fields
        assert "status" not in ArticleOut.model_fields


class TestModelSchemaClassOptional:
    def test_all_optional(self):
        class ArticleUpdate(ModelSchema):
            class Meta:
                model = Article
                fields = ["title", "body"]
                all_optional = True

        assert ArticleUpdate.model_fields["title"].default is None
        assert ArticleUpdate.model_fields["body"].default is None

    def test_optional_fields_selective(self):
        class ArticleUpdate(ModelSchema):
            class Meta:
                model = Article
                fields = ["title", "body"]
                optional_fields = {"title"}

        assert ArticleUpdate.model_fields["title"].default is None
        assert ArticleUpdate.model_fields["body"].is_required()


class TestModelSchemaClassResourceType:
    def test_attaches_jsonapi_meta(self):
        class ArticleOut(ModelSchema):
            class Meta:
                model = Article
                fields = ["id", "title"]
                resource_type = "articles"

        assert hasattr(ArticleOut, "jsonapi_meta")
        assert ArticleOut.jsonapi_meta.resource_type == "articles"

    def test_id_field(self):
        class ArticleOut(ModelSchema):
            class Meta:
                model = Article
                fields = ["uuid", "title"]
                resource_type = "articles"
                id_field = "uuid"

        assert ArticleOut.jsonapi_meta.id_field == "uuid"

    def test_no_resource_type_no_meta(self):
        class ArticleOut(ModelSchema):
            class Meta:
                model = Article
                fields = ["id", "title"]

        assert not hasattr(ArticleOut, "jsonapi_meta")

    def test_detected_by_get_jsonapi_meta(self):
        from django_ninja_jsonapi.meta import get_jsonapi_meta

        class ArticleOut(ModelSchema):
            class Meta:
                model = Article
                fields = ["id", "title"]
                resource_type = "articles"

        meta = get_jsonapi_meta(ArticleOut)
        assert meta is not None
        assert meta.resource_type == "articles"

    def test_transparent_layer_compatibility(self):
        from django_ninja_jsonapi.meta import _is_jsonapi_schema

        class ArticleOut(ModelSchema):
            class Meta:
                model = Article
                fields = ["id", "title"]
                resource_type = "articles"

        assert _is_jsonapi_schema(ArticleOut)


class TestModelSchemaClassExtraFields:
    def test_user_declared_fields_merged(self):
        class ArticleOut(ModelSchema):
            custom_score: float = 0.0

            class Meta:
                model = Article
                fields = ["id", "title"]

        assert "id" in ArticleOut.model_fields
        assert "title" in ArticleOut.model_fields
        assert "custom_score" in ArticleOut.model_fields
        instance: Any = ArticleOut.model_validate({"id": 1, "title": "Hello"})
        assert instance.custom_score == 0.0

    def test_user_declared_overrides_auto(self):
        class ArticleOut(ModelSchema):
            title: str  # Override: always required (no Optional)

            class Meta:
                model = Article
                fields = ["id", "title"]

        assert ArticleOut.model_fields["title"].is_required()


class TestModelSchemaClassProperties:
    def test_property_field_included(self):
        class ArticleOut(ModelSchema):
            class Meta:
                model = Article
                fields = ["title", "organization_name"]

        assert "organization_name" in ArticleOut.model_fields

    def test_unknown_field_raises(self):
        with pytest.raises(ValueError, match="not found"):

            class Bad(ModelSchema):
                class Meta:
                    model = Article
                    fields = ["nonexistent_field"]


class TestModelSchemaClassValidation:
    def test_validates_dict_data(self):
        class ArticleOut(ModelSchema):
            class Meta:
                model = Article
                fields = ["title", "body"]

        instance: Any = ArticleOut.model_validate({"title": "Hello", "body": "World"})
        assert instance.title == "Hello"
        assert instance.body == "World"

    def test_validates_from_attributes(self):
        class ArticleOut(ModelSchema):
            class Meta:
                model = Article
                fields = ["title", "body"]

        class FakeObj:
            title = "Hello"
            body = "World"

        instance: Any = ArticleOut.model_validate(FakeObj(), from_attributes=True)
        assert instance.title == "Hello"
        assert instance.body == "World"
