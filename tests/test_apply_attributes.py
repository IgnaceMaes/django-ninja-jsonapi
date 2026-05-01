"""Tests for apply_attributes helper."""

from unittest.mock import MagicMock

from pydantic import BaseModel

from django_ninja_jsonapi.helpers import apply_attributes
from django_ninja_jsonapi.schema_factory import jsonapi_body


class ArticleUpdateSchema(BaseModel):
    title: str | None = None
    body: str | None = None
    status: str | None = None


class TestApplyAttributes:
    def _make_body(self, attrs: dict, *, schema=ArticleUpdateSchema):
        BodyModel = jsonapi_body(schema, "articles")
        return BodyModel.model_validate(
            {
                "data": {
                    "type": "articles",
                    "attributes": attrs,
                }
            }
        )

    def test_sets_attributes_on_instance(self):
        instance = MagicMock()
        body = self._make_body({"title": "New Title", "status": "published"})

        result = apply_attributes(instance, body, save=False)

        assert instance.title == "New Title"
        assert instance.status == "published"
        assert result == {"title": "New Title", "status": "published"}

    def test_saves_with_update_fields(self):
        instance = MagicMock()
        body = self._make_body({"title": "New Title"})

        apply_attributes(instance, body)

        instance.save.assert_called_once()
        save_kwargs = instance.save.call_args
        assert set(save_kwargs[1]["update_fields"]) == {"title"}

    def test_extra_update_fields(self):
        instance = MagicMock()
        body = self._make_body({"title": "New Title"})

        apply_attributes(instance, body, extra_update_fields=["updated_dt"])

        save_kwargs = instance.save.call_args
        assert "updated_dt" in save_kwargs[1]["update_fields"]
        assert "title" in save_kwargs[1]["update_fields"]

    def test_exclude_fields(self):
        instance = MagicMock()
        body = self._make_body({"title": "New Title", "status": "published"})

        result = apply_attributes(instance, body, save=False, exclude={"status"})

        assert result == {"title": "New Title"}
        assert not hasattr(instance, "status") or instance.status != "published"

    def test_no_save_when_no_attributes_changed(self):
        instance = MagicMock()
        # With exclude_unset, only explicitly set fields are included.
        # Here we send an empty body (all fields are optional and unset).
        BodyModel = jsonapi_body(ArticleUpdateSchema, "articles")
        body = BodyModel.model_validate(
            {
                "data": {
                    "type": "articles",
                    "attributes": {},
                }
            }
        )

        apply_attributes(instance, body)

        instance.save.assert_not_called()

    def test_save_false_skips_save(self):
        instance = MagicMock()
        body = self._make_body({"title": "New Title"})

        apply_attributes(instance, body, save=False)

        instance.save.assert_not_called()

    def test_returns_applied_attrs_dict(self):
        instance = MagicMock()
        body = self._make_body({"title": "Hello", "body": "Content"})

        result = apply_attributes(instance, body, save=False)

        assert result == {"title": "Hello", "body": "Content"}
