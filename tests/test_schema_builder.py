import logging

from django_ninja_jsonapi.schema_base import BaseModel
from django_ninja_jsonapi.schema_builder import SchemaBuilder


class OutputSchema(BaseModel):
    name: str


class InputSchema(BaseModel):
    name: str


def test_create_schemas_warns_when_write_schemas_default_to_output_schema(caplog, monkeypatch):
    builder = SchemaBuilder(resource_type="customer")

    monkeypatch.setattr(builder, "build_schema_in", lambda **kwargs: (kwargs["schema_in"], kwargs["schema_in"]))
    monkeypatch.setattr(builder, "_create_schemas_objects_list", lambda schema: schema)
    monkeypatch.setattr(builder, "_create_schemas_object_detail", lambda schema: schema)

    with caplog.at_level(logging.WARNING, logger="django_ninja_jsonapi.schema_builder"):
        builder.create_schemas(schema=OutputSchema)

    warning_messages = [record.getMessage() for record in caplog.records]
    assert any("schema_in_post" in message for message in warning_messages)
    assert any("schema_in_patch" in message for message in warning_messages)


def test_create_schemas_does_not_warn_when_write_schemas_are_explicit(caplog, monkeypatch):
    builder = SchemaBuilder(resource_type="customer")

    monkeypatch.setattr(builder, "build_schema_in", lambda **kwargs: (kwargs["schema_in"], kwargs["schema_in"]))
    monkeypatch.setattr(builder, "_create_schemas_objects_list", lambda schema: schema)
    monkeypatch.setattr(builder, "_create_schemas_object_detail", lambda schema: schema)

    with caplog.at_level(logging.WARNING, logger="django_ninja_jsonapi.schema_builder"):
        builder.create_schemas(
            schema=OutputSchema,
            schema_in_post=InputSchema,
            schema_in_patch=InputSchema,
        )

    warning_messages = [record.getMessage() for record in caplog.records]
    assert not any("schema_in_post" in message for message in warning_messages)
    assert not any("schema_in_patch" in message for message in warning_messages)
