"""Tests for get_rel_id / get_rel_ids helpers on jsonapi_body models."""

import pytest
from pydantic import BaseModel

from django_ninja_jsonapi.schema_factory import JsonApiBody, JsonApiDataIn, jsonapi_body


class ArticleCreateSchema(BaseModel):
    title: str
    body: str


# ---------------------------------------------------------------------------
# get_rel_id — to-one relationship
# ---------------------------------------------------------------------------


class TestGetRelId:
    def test_returns_id_for_present_relationship(self):
        BodyModel = jsonapi_body(
            ArticleCreateSchema,
            "articles",
            relationships={"author": {"resource_type": "people"}},
        )

        parsed = BodyModel.model_validate(
            {
                "data": {
                    "type": "articles",
                    "attributes": {"title": "Hello", "body": "World"},
                    "relationships": {
                        "author": {"data": {"id": "42", "type": "people"}},
                    },
                }
            }
        )

        assert parsed.data.get_rel_id("author") == "42"

    def test_returns_none_when_relationship_absent(self):
        BodyModel = jsonapi_body(
            ArticleCreateSchema,
            "articles",
            relationships={"author": {"resource_type": "people"}},
        )

        parsed = BodyModel.model_validate(
            {
                "data": {
                    "type": "articles",
                    "attributes": {"title": "Hello", "body": "World"},
                }
            }
        )

        assert parsed.data.get_rel_id("author") is None

    def test_returns_none_for_unknown_relationship(self):
        BodyModel = jsonapi_body(ArticleCreateSchema, "articles")

        parsed = BodyModel.model_validate(
            {
                "data": {
                    "type": "articles",
                    "attributes": {"title": "Hello", "body": "World"},
                }
            }
        )

        assert parsed.data.get_rel_id("nonexistent") is None

    def test_returns_none_when_relationship_data_is_none(self):
        BodyModel = jsonapi_body(
            ArticleCreateSchema,
            "articles",
            relationships={"author": {"resource_type": "people"}},
        )

        parsed = BodyModel.model_validate(
            {
                "data": {
                    "type": "articles",
                    "attributes": {"title": "Hello", "body": "World"},
                    "relationships": {},
                }
            }
        )

        assert parsed.data.get_rel_id("author") is None

    def test_shortcut_on_body_model(self):
        BodyModel = jsonapi_body(
            ArticleCreateSchema,
            "articles",
            relationships={"author": {"resource_type": "people"}},
        )

        parsed = BodyModel.model_validate(
            {
                "data": {
                    "type": "articles",
                    "attributes": {"title": "Hello", "body": "World"},
                    "relationships": {
                        "author": {"data": {"id": "42", "type": "people"}},
                    },
                }
            }
        )

        # Top-level shortcut
        assert parsed.get_rel_id("author") == "42"


# ---------------------------------------------------------------------------
# get_rel_ids — to-many relationship
# ---------------------------------------------------------------------------


class TestGetRelIds:
    def test_returns_ids_for_present_relationship(self):
        BodyModel = jsonapi_body(
            ArticleCreateSchema,
            "articles",
            relationships={"tags": {"resource_type": "tags", "many": True}},
        )

        parsed = BodyModel.model_validate(
            {
                "data": {
                    "type": "articles",
                    "attributes": {"title": "Hello", "body": "World"},
                    "relationships": {
                        "tags": {
                            "data": [
                                {"id": "1", "type": "tags"},
                                {"id": "2", "type": "tags"},
                                {"id": "3", "type": "tags"},
                            ]
                        }
                    },
                }
            }
        )

        assert parsed.data.get_rel_ids("tags") == ["1", "2", "3"]

    def test_returns_empty_list_when_relationship_absent(self):
        BodyModel = jsonapi_body(
            ArticleCreateSchema,
            "articles",
            relationships={"tags": {"resource_type": "tags", "many": True}},
        )

        parsed = BodyModel.model_validate(
            {
                "data": {
                    "type": "articles",
                    "attributes": {"title": "Hello", "body": "World"},
                }
            }
        )

        assert parsed.data.get_rel_ids("tags") == []

    def test_returns_empty_list_for_unknown_relationship(self):
        BodyModel = jsonapi_body(ArticleCreateSchema, "articles")

        parsed = BodyModel.model_validate(
            {
                "data": {
                    "type": "articles",
                    "attributes": {"title": "Hello", "body": "World"},
                }
            }
        )

        assert parsed.data.get_rel_ids("nonexistent") == []

    def test_shortcut_on_body_model(self):
        BodyModel = jsonapi_body(
            ArticleCreateSchema,
            "articles",
            relationships={"tags": {"resource_type": "tags", "many": True}},
        )

        parsed = BodyModel.model_validate(
            {
                "data": {
                    "type": "articles",
                    "attributes": {"title": "Hello", "body": "World"},
                    "relationships": {
                        "tags": {
                            "data": [
                                {"id": "1", "type": "tags"},
                                {"id": "2", "type": "tags"},
                            ]
                        }
                    },
                }
            }
        )

        # Top-level shortcut
        assert parsed.get_rel_ids("tags") == ["1", "2"]


# ---------------------------------------------------------------------------
# Generic base classes — type identity
# ---------------------------------------------------------------------------


class TestGenericBaseClasses:
    def test_body_model_is_subclass_of_JsonApiBody(self):
        BodyModel = jsonapi_body(ArticleCreateSchema, "articles")
        assert issubclass(BodyModel, JsonApiBody)

    def test_data_model_is_subclass_of_JsonApiDataIn(self):
        BodyModel = jsonapi_body(ArticleCreateSchema, "articles")
        DataModel = BodyModel.model_fields["data"].annotation
        assert issubclass(DataModel, JsonApiDataIn)
