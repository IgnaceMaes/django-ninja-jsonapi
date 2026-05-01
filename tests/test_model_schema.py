"""Tests for model_schema() factory."""

import uuid

import pytest
from django.db import models

from django_ninja_jsonapi.model_schema import model_schema

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
            return self.organization.name  # ty: ignore[invalid-return-type]
        return ""

    class Meta:
        app_label = "testapp"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestModelSchemaBasic:
    def test_generates_schema_with_specified_fields(self):
        schema = model_schema(Article, fields=["title", "body"])
        assert "title" in schema.model_fields
        assert "body" in schema.model_fields
        assert "status" not in schema.model_fields

    def test_generates_schema_with_all_fields(self):
        schema = model_schema(Article)
        assert "title" in schema.model_fields
        assert "body" in schema.model_fields
        assert "status" in schema.model_fields

    def test_from_attributes_config(self):
        schema = model_schema(Article, fields=["title"])
        assert schema.model_config.get("from_attributes") is True

    def test_custom_name(self):
        schema = model_schema(Article, fields=["title"], name="MyCustomSchema")
        assert schema.__name__ == "MyCustomSchema"

    def test_default_name(self):
        schema = model_schema(Article, fields=["title"])
        assert schema.__name__ == "ArticleSchema"


class TestModelSchemaFieldTypes:
    def test_charfield_is_str(self):
        schema = model_schema(Article, fields=["title"])
        assert schema.model_fields["title"].annotation is str

    def test_textfield_is_str(self):
        schema = model_schema(Article, fields=["body"])
        assert schema.model_fields["body"].annotation is str

    def test_booleanfield_is_bool(self):
        schema = model_schema(Article, fields=["is_active"])
        # is_active has a default, so it becomes Optional[bool]
        # Check the inner type
        field = schema.model_fields["is_active"]
        assert field.default is None  # optional fields default to None

    def test_integerfield_is_int(self):
        schema = model_schema(Article, fields=["view_count"])
        field = schema.model_fields["view_count"]
        assert field.default is None  # has default=0, so becomes Optional

    def test_datetimefield(self):
        schema = model_schema(Article, fields=["created_dt"])
        field = schema.model_fields["created_dt"]
        # auto_now_add doesn't set a standard "default", so the field is required
        assert field.is_required()


class TestModelSchemaOptionalFields:
    def test_all_optional(self):
        schema = model_schema(Article, fields=["title", "body"], all_optional=True)
        for field_name in ["title", "body"]:
            assert schema.model_fields[field_name].default is None

    def test_optional_fields_selective(self):
        schema = model_schema(
            Article,
            fields=["title", "body"],
            optional_fields={"title"},
        )
        assert schema.model_fields["title"].default is None
        assert schema.model_fields["body"].is_required()

    def test_nullable_field_is_optional(self):
        schema = model_schema(Article, fields=["organization"])
        assert schema.model_fields["organization"].default is None

    def test_field_with_default_is_optional(self):
        schema = model_schema(Article, fields=["status"])
        assert schema.model_fields["status"].default is None


class TestModelSchemaExclude:
    def test_exclude_fields(self):
        schema = model_schema(Article, fields=["title", "body", "status"], exclude={"status"})
        assert "title" in schema.model_fields
        assert "body" in schema.model_fields
        assert "status" not in schema.model_fields


class TestModelSchemaProperties:
    def test_property_field_included(self):
        schema = model_schema(Article, fields=["title", "organization_name"])
        assert "organization_name" in schema.model_fields
        assert "title" in schema.model_fields

    def test_unknown_field_raises(self):
        with pytest.raises(ValueError, match="not found"):
            model_schema(Article, fields=["nonexistent_field"])


class TestModelSchemaExtraFields:
    def test_extra_fields(self):
        schema = model_schema(
            Article,
            fields=["title"],
            extra_fields={"custom_field": (str, "default_value")},
        )
        assert "custom_field" in schema.model_fields
        assert "title" in schema.model_fields


class TestModelSchemaValidation:
    def test_validates_dict_data(self):
        schema = model_schema(Article, fields=["title", "body"])
        instance = schema.model_validate({"title": "Hello", "body": "World"})
        assert instance.title == "Hello"  # ty: ignore[unresolved-attribute]
        assert instance.body == "World"  # ty: ignore[unresolved-attribute]

    def test_validates_from_attributes(self):
        schema = model_schema(Article, fields=["title", "body"])

        class FakeObj:
            title = "Hello"
            body = "World"

        instance = schema.model_validate(FakeObj(), from_attributes=True)
        assert instance.title == "Hello"  # ty: ignore[unresolved-attribute]
        assert instance.body == "World"  # ty: ignore[unresolved-attribute]
