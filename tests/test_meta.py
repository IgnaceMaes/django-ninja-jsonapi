"""Tests for JsonApiMeta, auto-relationship detection, and related utilities."""

from typing import ClassVar

import pytest
from pydantic import BaseModel, ConfigDict

from django_ninja_jsonapi.meta import (
    JsonApiMeta,
    _dasherize,
    _pluralize,
    detect_relationships,
    get_jsonapi_meta,
    get_or_default_meta,
)
from django_ninja_jsonapi.renderers import JSONAPIRelationshipConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class TestPluralize:
    def test_regular(self):
        assert _pluralize("article") == "articles"

    def test_ends_with_s(self):
        assert _pluralize("bus") == "buses"

    def test_ends_with_x(self):
        assert _pluralize("box") == "boxes"

    def test_ends_with_sh(self):
        assert _pluralize("brush") == "brushes"

    def test_ends_with_ch(self):
        assert _pluralize("match") == "matches"

    def test_ends_with_consonant_y(self):
        assert _pluralize("category") == "categories"

    def test_ends_with_vowel_y(self):
        assert _pluralize("day") == "days"


class TestDasherize:
    def test_camel_case(self):
        assert _dasherize("IntakeConfig") == "intake-config"

    def test_snake_case(self):
        assert _dasherize("intake_config") == "intake-config"

    def test_simple(self):
        assert _dasherize("Article") == "article"

    def test_multi_word_camel(self):
        assert _dasherize("MyGreatResource") == "my-great-resource"


# ---------------------------------------------------------------------------
# JsonApiMeta
# ---------------------------------------------------------------------------


class TestJsonApiMeta:
    def test_explicit_resource_type(self):
        meta = JsonApiMeta(resource_type="articles")

        class S(BaseModel):
            id: int

        assert meta.resolve_resource_type(S) == "articles"

    def test_inferred_resource_type_strips_schema_suffix(self):
        meta = JsonApiMeta()

        class ArticleSchema(BaseModel):
            id: int

        assert meta.resolve_resource_type(ArticleSchema) == "articles"

    def test_inferred_resource_type_camel_case(self):
        meta = JsonApiMeta()

        class IntakeConfigSchema(BaseModel):
            id: int

        assert meta.resolve_resource_type(IntakeConfigSchema) == "intake-configs"

    def test_explicit_id_field(self):
        meta = JsonApiMeta(id_field="uuid")

        class S(BaseModel):
            uuid: str

        assert meta.resolve_id_field(S) == "uuid"

    def test_inferred_id_field_defaults_to_id(self):
        meta = JsonApiMeta()

        class S(BaseModel):
            id: int

        assert meta.resolve_id_field(S) == "id"

    def test_inferred_id_field_falls_back_to_uuid(self):
        meta = JsonApiMeta()

        class S(BaseModel):
            uuid: str
            title: str

        assert meta.resolve_id_field(S) == "uuid"

    def test_inferred_id_field_prefers_id_over_uuid(self):
        meta = JsonApiMeta()

        class S(BaseModel):
            id: int
            uuid: str

        assert meta.resolve_id_field(S) == "id"


# ---------------------------------------------------------------------------
# get_jsonapi_meta / get_or_default_meta
# ---------------------------------------------------------------------------


class TestGetJsonApiMeta:
    def test_returns_none_for_plain_schema(self):
        class S(BaseModel):
            id: int

        assert get_jsonapi_meta(S) is None

    def test_returns_meta_when_present(self):
        class S(BaseModel):
            id: int
            jsonapi_meta: ClassVar[JsonApiMeta] = JsonApiMeta(resource_type="things")

        meta = get_jsonapi_meta(S)
        assert meta is not None
        assert meta.resolve_resource_type(S) == "things"


class TestGetOrDefaultMeta:
    def test_returns_meta_when_present(self):
        class S(BaseModel):
            id: int
            jsonapi_meta: ClassVar[JsonApiMeta] = JsonApiMeta(resource_type="things")

        meta = get_or_default_meta(S)
        assert meta.resolve_resource_type(S) == "things"

    def test_returns_default_when_not_present(self):
        class ArticleSchema(BaseModel):
            id: int

        meta = get_or_default_meta(ArticleSchema)
        assert meta.resolve_resource_type(ArticleSchema) == "articles"


# ---------------------------------------------------------------------------
# Auto-relationship detection
# ---------------------------------------------------------------------------


class TagSchema(BaseModel):
    id: int
    name: str
    jsonapi_meta: ClassVar[JsonApiMeta] = JsonApiMeta(resource_type="tags")


class UserSchema(BaseModel):
    id: int
    name: str
    jsonapi_meta: ClassVar[JsonApiMeta] = JsonApiMeta(resource_type="people", id_field="id")


class ArticleSchema(BaseModel):
    id: int
    title: str
    body: str
    author: UserSchema | None = None
    tags: list[TagSchema] = []
    jsonapi_meta: ClassVar[JsonApiMeta] = JsonApiMeta(resource_type="articles")


class TestDetectRelationships:
    def test_detects_to_one_relationship(self):
        rels = detect_relationships(ArticleSchema)
        assert "author" in rels
        assert rels["author"].resource_type == "people"
        assert rels["author"].many is False

    def test_detects_to_many_relationship(self):
        rels = detect_relationships(ArticleSchema)
        assert "tags" in rels
        assert rels["tags"].resource_type == "tags"
        assert rels["tags"].many is True

    def test_non_relationship_fields_excluded(self):
        rels = detect_relationships(ArticleSchema)
        assert "title" not in rels
        assert "body" not in rels
        assert "id" not in rels

    def test_no_relationships(self):
        rels = detect_relationships(TagSchema)
        assert rels == {}

    def test_plain_schema_without_meta_not_detected(self):
        class PlainSchema(BaseModel):
            id: int
            name: str

        class ParentSchema(BaseModel):
            id: int
            child: PlainSchema | None = None
            jsonapi_meta: ClassVar[JsonApiMeta] = JsonApiMeta(resource_type="parents")

        rels = detect_relationships(ParentSchema)
        assert "child" not in rels

    def test_uses_related_schema_id_field(self):
        class CustomIdSchema(BaseModel):
            uuid: str
            name: str
            jsonapi_meta: ClassVar[JsonApiMeta] = JsonApiMeta(resource_type="customs", id_field="uuid")

        class ParentSchema(BaseModel):
            id: int
            ref: CustomIdSchema | None = None
            jsonapi_meta: ClassVar[JsonApiMeta] = JsonApiMeta(resource_type="parents")

        rels = detect_relationships(ParentSchema)
        assert rels["ref"].id_field == "uuid"
