from __future__ import annotations

import inspect
from functools import wraps
from typing import Any, Callable

from django.conf import settings
from django.http import HttpRequest

from django_ninja_jsonapi.renderers import (
    REQUEST_JSONAPI_CONFIG_ATTR,
    JSONAPIRelationshipConfig,
    JSONAPIResourceConfig,
    normalize_relationships,
)

_UNSET = object()


def jsonapi_resource(
    resource_type: str,
    *,
    id_field: str = "id",
    include_jsonapi_object: object = _UNSET,
    jsonapi_version: str | None = None,
    relationships: dict[str, JSONAPIRelationshipConfig | dict[str, Any]] | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    relationship_config = normalize_relationships(relationships)

    def _resolve_config() -> JSONAPIResourceConfig:
        ninja_jsonapi = getattr(settings, "NINJA_JSONAPI", {})
        resolved_include = (
            ninja_jsonapi.get("INCLUDE_JSONAPI_OBJECT", False)
            if include_jsonapi_object is _UNSET
            else include_jsonapi_object
        )
        resolved_version = jsonapi_version or ninja_jsonapi.get("JSONAPI_VERSION", "1.0")
        return JSONAPIResourceConfig(
            resource_type=resource_type,
            id_field=id_field,
            include_jsonapi_object=bool(resolved_include),
            jsonapi_version=str(resolved_version),
            relationships=relationship_config,
        )

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                request = _extract_request(args=args, kwargs=kwargs)
                setattr(request, REQUEST_JSONAPI_CONFIG_ATTR, _resolve_config())
                return await func(*args, **kwargs)

            return async_wrapper

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            request = _extract_request(args=args, kwargs=kwargs)
            setattr(request, REQUEST_JSONAPI_CONFIG_ATTR, _resolve_config())
            return func(*args, **kwargs)

        return sync_wrapper

    return decorator


def _extract_request(*, args: tuple[Any, ...], kwargs: dict[str, Any]) -> HttpRequest:
    request = kwargs.get("request")
    if isinstance(request, HttpRequest):
        return request

    for arg in args:
        if isinstance(arg, HttpRequest):
            return arg

    msg = "jsonapi_resource decorator could not locate request argument"
    raise ValueError(msg)
