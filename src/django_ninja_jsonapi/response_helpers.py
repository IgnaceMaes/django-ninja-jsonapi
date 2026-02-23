from __future__ import annotations

from typing import Any

from django.http import HttpRequest

from django_ninja_jsonapi.renderers import (
    REQUEST_JSONAPI_INCLUDED_ATTR,
    REQUEST_JSONAPI_LINKS_ATTR,
    REQUEST_JSONAPI_META_ATTR,
    JSONAPIIncludedEntry,
    JSONAPIRelationshipConfig,
    JSONAPIResourceConfig,
)


def jsonapi_include(
    request: HttpRequest,
    data: Any,
    *,
    resource_type: str,
    id_field: str = "id",
    relationships: dict[str, JSONAPIRelationshipConfig | dict[str, Any]] | None = None,
) -> None:
    config = JSONAPIResourceConfig(
        resource_type=resource_type,
        id_field=id_field,
        relationships=_normalize_relationships(relationships),
    )
    current: list[JSONAPIIncludedEntry] = list(getattr(request, REQUEST_JSONAPI_INCLUDED_ATTR, []) or [])
    current.append(JSONAPIIncludedEntry(data=data, config=config))
    setattr(request, REQUEST_JSONAPI_INCLUDED_ATTR, current)


def jsonapi_meta(request: HttpRequest, **meta_values: Any) -> None:
    current_meta = dict(getattr(request, REQUEST_JSONAPI_META_ATTR, {}) or {})
    current_meta.update(meta_values)
    setattr(request, REQUEST_JSONAPI_META_ATTR, current_meta)


def jsonapi_links(request: HttpRequest, **links: str) -> None:
    current_links = dict(getattr(request, REQUEST_JSONAPI_LINKS_ATTR, {}) or {})
    current_links.update(links)
    setattr(request, REQUEST_JSONAPI_LINKS_ATTR, current_links)


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