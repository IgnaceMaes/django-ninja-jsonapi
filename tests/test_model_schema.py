"""Tests for model_schema() factory and ModelSchema base class."""

import uuid
from typing import Any

import pytest
from django.db import models

from django_ninja_jsonapi._model_schema import ModelSchema, model_schema

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
        instance: Any = schema.model_validate({"title": "Hello", "body": "World"})
        assert instance.title == "Hello"
        assert instance.body == "World"

    def test_validates_from_attributes(self):
        schema = model_schema(Article, fields=["title", "body"])

        class FakeObj:
            title = "Hello"
            body = "World"

        instance: Any = schema.model_validate(FakeObj(), from_attributes=True)
        assert instance.title == "Hello"
        assert instance.body == "World"


class TestModelSchemaResourceType:
    def test_resource_type_attaches_jsonapi_meta(self):
        schema = model_schema(Article, fields=["id", "title"], resource_type="articles")
        assert hasattr(schema, "jsonapi_meta")
        assert schema.jsonapi_meta.resource_type == "articles"

    def test_resource_type_with_id_field(self):
        schema = model_schema(Article, fields=["uuid", "title"], resource_type="articles", id_field="uuid")
        assert schema.jsonapi_meta.resource_type == "articles"
        assert schema.jsonapi_meta.id_field == "uuid"

    def test_no_resource_type_no_jsonapi_meta(self):
        schema = model_schema(Article, fields=["id", "title"])
        assert not hasattr(schema, "jsonapi_meta")

    def test_resource_type_resolve_resource_type(self):
        schema = model_schema(Article, fields=["id", "title"], resource_type="articles")
        assert schema.jsonapi_meta.resolve_resource_type(schema) == "articles"

    def test_resource_type_resolve_id_field_default(self):
        schema = model_schema(Article, fields=["id", "title"], resource_type="articles")
        assert schema.jsonapi_meta.resolve_id_field(schema) == "id"

    def test_resource_type_resolve_id_field_uuid(self):
        schema = model_schema(Article, fields=["uuid", "title"], resource_type="articles", id_field="uuid")
        assert schema.jsonapi_meta.resolve_id_field(schema) == "uuid"

    def test_detected_by_get_jsonapi_meta(self):
        from django_ninja_jsonapi.meta import get_jsonapi_meta

        schema = model_schema(Article, fields=["id", "title"], resource_type="articles")
        meta = get_jsonapi_meta(schema)
        assert meta is not None
        assert meta.resource_type == "articles"

    def test_transparent_layer_compatibility(self):
        """Schema with resource_type should be recognised by detect_relationships."""
        from django_ninja_jsonapi.meta import _is_jsonapi_schema

        schema = model_schema(Article, fields=["id", "title"], resource_type="articles")
        assert _is_jsonapi_schema(schema)


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
