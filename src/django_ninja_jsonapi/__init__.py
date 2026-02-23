"""JSON API utils package."""

from pathlib import Path
from typing import Any

from django_ninja_jsonapi.exceptions import BadRequest
from django_ninja_jsonapi.exceptions.json_api import HTTPException
from django_ninja_jsonapi.querystring import QueryStringManager
from django_ninja_jsonapi.renderers import JSONAPIRenderer
from django_ninja_jsonapi.response_helpers import jsonapi_include, jsonapi_links, jsonapi_meta

__version__ = Path(__file__).parent.joinpath("VERSION").read_text().strip()

__all__ = [
    "ApplicationBuilder",
    "BadRequest",
    "HTTPException",
    "JSONAPIRenderer",
    "QueryStringManager",
    "ViewBaseGeneric",
    "jsonapi_include",
    "jsonapi_links",
    "jsonapi_meta",
    "jsonapi_resource",
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

    raise AttributeError(name)
