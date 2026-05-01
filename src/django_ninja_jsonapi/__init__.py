"""JSON API utils package."""

from pathlib import Path
from typing import Any

from django_ninja_jsonapi.exceptions import BadRequest, NotFound
from django_ninja_jsonapi.exceptions.json_api import HTTPException
from django_ninja_jsonapi.querystring import QueryStringManager
from django_ninja_jsonapi.renderers import JSONAPIRenderer
from django_ninja_jsonapi.response_helpers import (
    jsonapi_cursor_pagination,
    jsonapi_include,
    jsonapi_links,
    jsonapi_meta,
    jsonapi_paginate,
    jsonapi_pagination,
)

__version__ = Path(__file__).parent.joinpath("VERSION").read_text().strip()

__all__ = [
    "ApplicationBuilder",
    "BadRequest",
    "HTTPException",
    "JSONAPIRenderer",
    "JsonApiBody",
    "JsonApiDataIn",
    "JsonApiResource",
    "NotFound",
    "QueryStringManager",
    "ViewBaseGeneric",
    "apply_attributes",
    "jsonapi_body",
    "jsonapi_cursor_pagination",
    "jsonapi_filter",
    "jsonapi_include",
    "jsonapi_links",
    "jsonapi_meta",
    "jsonapi_paginate",
    "jsonapi_pagination",
    "jsonapi_resource",
    "jsonapi_response",
    "jsonapi_sort",
    "model_schema",
    "parse_include",
    "setup_jsonapi",
]


def __getattr__(name: str) -> Any:
    if name == "ApplicationBuilder":
        from django_ninja_jsonapi.api.application_builder import ApplicationBuilder

        return ApplicationBuilder

    if name == "ViewBaseGeneric":
        from django_ninja_jsonapi.generics import ViewBaseGeneric

        return ViewBaseGeneric

    if name == "jsonapi_resource":
        from django_ninja_jsonapi.decorators import jsonapi_resource

        return jsonapi_resource

    if name == "jsonapi_response":
        from django_ninja_jsonapi.schema_factory import jsonapi_response

        return jsonapi_response

    if name == "jsonapi_body":
        from django_ninja_jsonapi.schema_factory import jsonapi_body

        return jsonapi_body

    if name == "JsonApiBody":
        from django_ninja_jsonapi.schema_factory import JsonApiBody

        return JsonApiBody

    if name == "JsonApiDataIn":
        from django_ninja_jsonapi.schema_factory import JsonApiDataIn

        return JsonApiDataIn

    if name == "setup_jsonapi":
        from django_ninja_jsonapi.setup import setup_jsonapi

        return setup_jsonapi

    if name == "jsonapi_sort":
        from django_ninja_jsonapi.response_helpers import jsonapi_sort

        return jsonapi_sort

    if name == "jsonapi_filter":
        from django_ninja_jsonapi.response_helpers import jsonapi_filter

        return jsonapi_filter

    if name == "parse_include":
        from django_ninja_jsonapi.response_helpers import parse_include

        return parse_include

    if name == "apply_attributes":
        from django_ninja_jsonapi.helpers import apply_attributes

        return apply_attributes

    if name == "JsonApiResource":
        from django_ninja_jsonapi.resource import JsonApiResource

        return JsonApiResource

    if name == "model_schema":
        from django_ninja_jsonapi.model_schema import model_schema

        return model_schema

    raise AttributeError(name)
