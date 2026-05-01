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
    "BadRequest",
    "HTTPException",
    "JSONAPIRenderer",
    "JsonApiMeta",
    "JsonApiNinja",
    "NotFound",
    "QueryStringManager",
    "apply_attributes",
    "get_rel_id",
    "get_rel_ids",
    "jsonapi_cursor_pagination",
    "jsonapi_filter",
    "jsonapi_include",
    "jsonapi_links",
    "jsonapi_meta",
    "jsonapi_paginate",
    "jsonapi_pagination",
    "jsonapi_sort",
    "model_schema",
    "parse_include",
]


def __getattr__(name: str) -> Any:
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

    if name == "model_schema":
        from django_ninja_jsonapi.model_schema import model_schema

        return model_schema

    if name == "JsonApiMeta":
        from django_ninja_jsonapi.meta import JsonApiMeta

        return JsonApiMeta

    if name == "JsonApiNinja":
        from django_ninja_jsonapi.transparent import JsonApiNinja

        return JsonApiNinja

    if name == "get_rel_id":
        from django_ninja_jsonapi.transparent import get_rel_id

        return get_rel_id

    if name == "get_rel_ids":
        from django_ninja_jsonapi.transparent import get_rel_ids

        return get_rel_ids

    raise AttributeError(name)
