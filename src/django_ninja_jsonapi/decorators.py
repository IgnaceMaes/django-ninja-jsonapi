from __future__ import annotations

import inspect
from functools import wraps
from typing import Any, Callable

from django.http import HttpRequest

from django_ninja_jsonapi.renderers import REQUEST_JSONAPI_CONFIG_ATTR, JSONAPIRelationshipConfig, JSONAPIResourceConfig


def jsonapi_resource(
    resource_type: str,
    *,
    id_field: str = "id",
    include_jsonapi_object: bool = True,
    jsonapi_version: str = "1.0",
    relationships: dict[str, JSONAPIRelationshipConfig | dict[str, Any]] | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    relationship_config = _normalize_relationships(relationships)
    config = JSONAPIResourceConfig(
        resource_type=resource_type,
        id_field=id_field,
        include_jsonapi_object=include_jsonapi_object,
        jsonapi_version=jsonapi_version,
        relationships=relationship_config,
    )

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                request = _extract_request(args=args, kwargs=kwargs)
                setattr(request, REQUEST_JSONAPI_CONFIG_ATTR, config)
                return await func(*args, **kwargs)

            return async_wrapper

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            request = _extract_request(args=args, kwargs=kwargs)
            setattr(request, REQUEST_JSONAPI_CONFIG_ATTR, config)
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


def _normalize_relationships(
    relationships: dict[str, JSONAPIRelationshipConfig | dict[str, Any]] | None,
) -> dict[str, JSONAPIRelationshipConfig]:
    if not relationships:
        return {}

    normalized: dict[str, JSONAPIRelationshipConfig] = {}
    for relationship_name, relationship_value in relationships.items():
        if isinstance(relationship_value, JSONAPIRelationshipConfig):
            normalized[relationship_name] = relationship_value
            continue

        normalized[relationship_name] = JSONAPIRelationshipConfig(
            resource_type=str(relationship_value["resource_type"]),
            many=bool(relationship_value.get("many", False)),
            id_field=str(relationship_value.get("id_field", "id")),
        )

    return normalized
