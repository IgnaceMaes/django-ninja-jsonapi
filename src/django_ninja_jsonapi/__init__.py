"""JSON API utils package."""

from pathlib import Path
from typing import Any

from django_ninja_jsonapi.exceptions import BadRequest
from django_ninja_jsonapi.exceptions.json_api import HTTPException
from django_ninja_jsonapi.querystring import QueryStringManager

__version__ = Path(__file__).parent.joinpath("VERSION").read_text().strip()

__all__ = [
    "ApplicationBuilder",
    "BadRequest",
    "HTTPException",
    "QueryStringManager",
    "ViewBaseGeneric",
]


def __getattr__(name: str) -> Any:
    if name == "ApplicationBuilder":
        from django_ninja_jsonapi.api.application_builder import ApplicationBuilder

        return ApplicationBuilder

    if name == "ViewBaseGeneric":
        from django_ninja_jsonapi.generics import ViewBaseGeneric

        return ViewBaseGeneric

    raise AttributeError(name)
