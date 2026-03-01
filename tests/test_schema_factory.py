import pytest
from pydantic import BaseModel

from django_ninja_jsonapi.renderers import JSONAPIRelationshipConfig
from django_ninja_jsonapi.schema_factory import jsonapi_body, jsonapi_response


class ArticleSchema(BaseModel):
    id: int
    title: str
    body: str


class ArticleCreateSchema(BaseModel):
    title: str
    body: str


class ArticleWithRelsSchema(BaseModel):
    id: int
    title: str
    author: dict | None = None
    tags: list[dict] | None = None


# ---------------------------------------------------------------------------
# jsonapi_response tests
# ---------------------------------------------------------------------------


class TestJsonapiResponse:
    def test_detail_response_has_correct_structure(self):
        ResponseModel = jsonapi_response(ArticleSchema, "articles")

        assert "data" in ResponseModel.model_fields
        assert "links" in ResponseModel.model_fields
        assert "jsonapi" in ResponseModel.model_fields
        assert "meta" in ResponseModel.model_fields
        assert "included" in ResponseModel.model_fields

    def test_detail_data_is_single_resource_object(self):
        ResponseModel = jsonapi_response(ArticleSchema, "articles")
        data_field = ResponseModel.model_fields["data"]
        # data should NOT be a list for detail
        assert not hasattr(data_field.annotation, "__origin__") or data_field.annotation.__origin__ is not list

    def test_list_response_data_is_collection(self):
        ResponseModel = jsonapi_response(ArticleSchema, "articles", many=True)
        data_field = ResponseModel.model_fields["data"]
        assert hasattr(data_field.annotation, "__origin__") and data_field.annotation.__origin__ is list

    def test_list_response_meta_has_pagination_fields(self):
        ResponseModel = jsonapi_response(ArticleSchema, "articles", many=True)
        meta_field = ResponseModel.model_fields["meta"]
        # The meta type should have count and totalPages
        from typing import get_args

        meta_types = get_args(meta_field.annotation)
        meta_type = next((t for t in meta_types if t is not type(None)), meta_field.annotation)
        assert "count" in meta_type.model_fields
        assert "totalPages" in meta_type.model_fields

    def test_resource_object_has_id_type_attributes(self):
        ResponseModel = jsonapi_response(ArticleSchema, "articles")
        data_type = ResponseModel.model_fields["data"].annotation

        assert "id" in data_type.model_fields
        assert "type" in data_type.model_fields
        assert "attributes" in data_type.model_fields

    def test_attributes_exclude_id_field(self):
        ResponseModel = jsonapi_response(ArticleSchema, "articles")
        data_type = ResponseModel.model_fields["data"].annotation
        attrs_type = data_type.model_fields["attributes"].annotation

        assert "id" not in attrs_type.model_fields
        assert "title" in attrs_type.model_fields
        assert "body" in attrs_type.model_fields

    def test_attributes_exclude_relationship_keys(self):
        ResponseModel = jsonapi_response(
            ArticleWithRelsSchema,
            "articles",
            relationships={"author": {"resource_type": "people"}},
        )
        data_type = ResponseModel.model_fields["data"].annotation
        attrs_type = data_type.model_fields["attributes"].annotation

        assert "author" not in attrs_type.model_fields
        assert "title" in attrs_type.model_fields

    def test_relationships_field_present_when_configured(self):
        ResponseModel = jsonapi_response(
            ArticleWithRelsSchema,
            "articles",
            relationships={
                "author": {"resource_type": "people"},
                "tags": {"resource_type": "tags", "many": True},
            },
        )
        data_type = ResponseModel.model_fields["data"].annotation
        assert "relationships" in data_type.model_fields

    def test_relationships_not_present_when_none(self):
        ResponseModel = jsonapi_response(ArticleSchema, "articles")
        data_type = ResponseModel.model_fields["data"].annotation
        assert "relationships" not in data_type.model_fields

    def test_caching_returns_same_model(self):
        model1 = jsonapi_response(ArticleSchema, "articles")
        model2 = jsonapi_response(ArticleSchema, "articles")
        assert model1 is model2

    def test_different_params_return_different_models(self):
        model1 = jsonapi_response(ArticleSchema, "articles")
        model2 = jsonapi_response(ArticleSchema, "articles", many=True)
        assert model1 is not model2

    def test_generated_model_validates_sample_document(self):
        ResponseModel = jsonapi_response(ArticleSchema, "articles")

        doc = ResponseModel.model_validate(
            {
                "data": {
                    "id": "1",
                    "type": "articles",
                    "attributes": {"title": "Hello", "body": "World"},
                },
                "links": {"self": "http://example.com/articles/1/"},
                "jsonapi": {"version": "1.0"},
            }
        )
        assert doc.data.id == "1"
        assert doc.data.type == "articles"
        assert doc.data.attributes.title == "Hello"

    def test_generated_list_model_validates(self):
        ResponseModel = jsonapi_response(ArticleSchema, "articles", many=True)

        doc = ResponseModel.model_validate(
            {
                "data": [
                    {
                        "id": "1",
                        "type": "articles",
                        "attributes": {"title": "A", "body": "B"},
                    },
                    {
                        "id": "2",
                        "type": "articles",
                        "attributes": {"title": "C", "body": "D"},
                    },
                ],
                "meta": {"count": 2, "totalPages": 1},
            }
        )
        assert len(doc.data) == 2

    def test_with_relationship_config_objects(self):
        ResponseModel = jsonapi_response(
            ArticleWithRelsSchema,
            "articles",
            relationships={
                "author": JSONAPIRelationshipConfig(resource_type="people"),
            },
        )
        data_type = ResponseModel.model_fields["data"].annotation
        assert "relationships" in data_type.model_fields


# ---------------------------------------------------------------------------
# jsonapi_body tests
# ---------------------------------------------------------------------------


class TestJsonapiBody:
    def test_basic_structure(self):
        BodyModel = jsonapi_body(ArticleCreateSchema, "articles")

        assert "data" in BodyModel.model_fields

    def test_data_has_type_and_attributes(self):
        BodyModel = jsonapi_body(ArticleCreateSchema, "articles")
        data_type = BodyModel.model_fields["data"].annotation

        assert "type" in data_type.model_fields
        assert "attributes" in data_type.model_fields

    def test_id_not_present_by_default(self):
        BodyModel = jsonapi_body(ArticleCreateSchema, "articles")
        data_type = BodyModel.model_fields["data"].annotation
        assert "id" not in data_type.model_fields

    def test_id_present_when_allow_id(self):
        BodyModel = jsonapi_body(ArticleCreateSchema, "articles", allow_id=True)
        data_type = BodyModel.model_fields["data"].annotation
        assert "id" in data_type.model_fields

    def test_relationships_present_when_configured(self):
        BodyModel = jsonapi_body(
            ArticleCreateSchema,
            "articles",
            relationships={"author": {"resource_type": "people"}},
        )
        data_type = BodyModel.model_fields["data"].annotation
        assert "relationships" in data_type.model_fields

    def test_relationships_not_present_when_none(self):
        BodyModel = jsonapi_body(ArticleCreateSchema, "articles")
        data_type = BodyModel.model_fields["data"].annotation
        assert "relationships" not in data_type.model_fields

    def test_caching_returns_same_model(self):
        model1 = jsonapi_body(ArticleCreateSchema, "articles")
        model2 = jsonapi_body(ArticleCreateSchema, "articles")
        assert model1 is model2

    def test_parses_valid_jsonapi_body(self):
        BodyModel = jsonapi_body(ArticleCreateSchema, "articles")

        parsed = BodyModel.model_validate(
            {
                "data": {
                    "type": "articles",
                    "attributes": {
                        "title": "Hello",
                        "body": "World",
                    },
                }
            }
        )
        assert parsed.data.type == "articles"
        assert parsed.data.attributes.title == "Hello"
        assert parsed.data.attributes.body == "World"

    def test_parses_body_with_relationships(self):
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
                        "author": {
                            "data": {"id": "9", "type": "people"},
                        }
                    },
                }
            }
        )
        assert parsed.data.relationships.author.data.id == "9"
        assert parsed.data.relationships.author.data.type == "people"

    def test_parses_body_with_many_relationship(self):
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
        assert len(parsed.data.relationships.tags.data) == 2

    def test_attributes_model_dump(self):
        BodyModel = jsonapi_body(ArticleCreateSchema, "articles")
        parsed = BodyModel.model_validate(
            {
                "data": {
                    "type": "articles",
                    "attributes": {"title": "Hello", "body": "World"},
                }
            }
        )
        attrs = parsed.data.attributes.model_dump()
        assert attrs == {"title": "Hello", "body": "World"}

    def test_rejects_invalid_type(self):
        BodyModel = jsonapi_body(ArticleCreateSchema, "articles")

        with pytest.raises(ValueError):
            BodyModel.model_validate(
                {
                    "data": {
                        "type": "wrong-type",
                        "attributes": {"title": "Hello", "body": "World"},
                    }
                }
            )

    def test_extra_fields_forbidden(self):
        BodyModel = jsonapi_body(ArticleCreateSchema, "articles")

        with pytest.raises(ValueError):
            BodyModel.model_validate(
                {
                    "data": {
                        "type": "articles",
                        "attributes": {"title": "Hello", "body": "World"},
                    },
                    "extra": "not allowed",
                }
            )
