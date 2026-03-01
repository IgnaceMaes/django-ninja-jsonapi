"""
Convenience setup for standalone JSON:API endpoints.
"""

from __future__ import annotations

from typing import Callable, Optional

from ninja import NinjaAPI

from django_ninja_jsonapi.exceptions import HTTPException
from django_ninja_jsonapi.exceptions.handlers import base_exception_handler
from django_ninja_jsonapi.renderers import JSONAPIRenderer


def setup_jsonapi(
    api: NinjaAPI,
    *,
    exception_handler: Optional[Callable] = None,
    renderer: Optional[JSONAPIRenderer] = None,
) -> None:
    """
    Configure a :class:`NinjaAPI` instance for JSON:API responses.

    This is a one-liner replacement for manually setting the renderer and
    registering the exception handler::

        from ninja import NinjaAPI
        from django_ninja_jsonapi import setup_jsonapi

        api = NinjaAPI()
        setup_jsonapi(api)

    It performs two actions:

    1. Sets ``api.renderer`` to a :class:`JSONAPIRenderer` (or a custom one).
    2. Registers :func:`base_exception_handler` (or a custom handler) for
       :class:`HTTPException` so that raised exceptions are returned as
       JSON:API error documents.
    """
    api.renderer = renderer or JSONAPIRenderer()

    handler = exception_handler or base_exception_handler
    add_handler = getattr(api, "add_exception_handler", None)
    if callable(add_handler):
        add_handler(HTTPException, handler)
