from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from ninja.renderers import JSONRenderer

JSONAPI_MEDIA_TYPE = "application/vnd.api+json"

REQUEST_JSONAPI_CONFIG_ATTR = "_jsonapi_resource_config"
REQUEST_JSONAPI_INCLUDED_ATTR = "_jsonapi_included"
REQUEST_JSONAPI_META_ATTR = "_jsonapi_meta"
REQUEST_JSONAPI_LINKS_ATTR = "_jsonapi_links"


@dataclass(frozen=True)
class JSONAPIRelationshipConfig:
    resource_type: str
    many: bool = False
    id_field: str = "id"


@dataclass(frozen=True)
class JSONAPIResourceConfig:
    resource_type: str
    id_field: str = "id"
    include_jsonapi_object: bool = True
    jsonapi_version: str = "1.0"
    relationships: dict[str, JSONAPIRelationshipConfig] = field(default_factory=dict)


@dataclass(frozen=True)
class JSONAPIIncludedEntry:
    data: Any
    config: JSONAPIResourceConfig


def normalize_relationships(
    relationships: dict[str, JSONAPIRelationshipConfig | dict[str, Any]] | None,
) -> dict[str, JSONAPIRelationshipConfig]:
    """Convert a dict of relationship configs (dataclass or plain dict) to normalized form."""
    if not relationships:
        return {}

    normalized: dict[str, JSONAPIRelationshipConfig] = {}
    for name, value in relationships.items():
        if isinstance(value, JSONAPIRelationshipConfig):
            normalized[name] = value
        else:
            normalized[name] = JSONAPIRelationshipConfig(
                resource_type=str(value["resource_type"]),
                many=bool(value.get("many", False)),
                id_field=str(value.get("id_field", "id")),
            )
    return normalized


class JSONAPIRenderer(JSONRenderer):
    media_type = JSONAPI_MEDIA_TYPE

    def render(self, request, data, *, response_status):
        resource_config = getattr(request, REQUEST_JSONAPI_CONFIG_ATTR, None)
        if resource_config is None:
            return super().render(request, data, response_status=response_status)

        wrapped_data = self._build_document(request=request, data=data, resource_config=resource_config)
        return super().render(request, wrapped_data, response_status=response_status)

    def _build_document(self, request, data: Any, resource_config: JSONAPIResourceConfig) -> dict[str, Any]:
        if self._is_jsonapi_document(data):
            return data

        is_collection = isinstance(data, list)
        if is_collection:
            primary_data = [
                self._build_resource_object(
                    item=item,
                    resource_config=resource_config,
                    request=request,
                    is_collection=True,
                )
                for item in data
            ]
        else:
            primary_data = self._build_resource_object(
                item=data,
                resource_config=resource_config,
                request=request,
                is_collection=False,
            )

        links = {"self": request.build_absolute_uri(request.get_full_path())}
        links.update(getattr(request, REQUEST_JSONAPI_LINKS_ATTR, {}) or {})

        response: dict[str, Any] = {
            "data": primary_data,
            "links": links,
        }

        if meta := getattr(request, REQUEST_JSONAPI_META_ATTR, None):
            response["meta"] = meta

        if resource_config.include_jsonapi_object:
            response["jsonapi"] = {"version": resource_config.jsonapi_version}

        included = self._build_included(request)
        if included:
            response["included"] = included

        return response

    def _build_included(self, request) -> list[dict[str, Any]]:
        included_entries = getattr(request, REQUEST_JSONAPI_INCLUDED_ATTR, None) or []
        result: list[dict[str, Any]] = []
        dedupe: set[tuple[str, str]] = set()

        for entry in included_entries:
            if isinstance(entry.data, list):
                items = entry.data
            else:
                items = [entry.data]

            for item in items:
                object_data = self._build_resource_object(
                    item=item,
                    resource_config=entry.config,
                    request=request,
                    is_collection=True,
                    use_resource_type_path=True,
                )
                if object_data is None:
                    continue

                dedupe_key = (object_data["type"], object_data["id"])
                if dedupe_key in dedupe:
                    continue

                dedupe.add(dedupe_key)
                result.append(object_data)

        return result

    def _build_resource_object(
        self,
        *,
        item: Any,
        resource_config: JSONAPIResourceConfig,
        request,
        is_collection: bool,
        use_resource_type_path: bool = False,
    ) -> Optional[dict[str, Any]]:
        if item is None:
            return None

        item = self._coerce_to_dict(item)

        item_id_value = item.get(resource_config.id_field)
        if item_id_value is None:
            msg = (
                "JSON:API renderer could not find an id value in response item. "
                f"Expected field {resource_config.id_field!r}."
            )
            raise ValueError(msg)

        item_id = str(item_id_value)

        relationship_keys = set(resource_config.relationships.keys())
        attributes = {
            key: value
            for key, value in item.items()
            if key not in relationship_keys and key != resource_config.id_field
        }

        response_item: dict[str, Any] = {
            "id": item_id,
            "type": resource_config.resource_type,
            "attributes": attributes,
            "links": {
                "self": self._build_item_self_link(
                    request=request,
                    item_id=item_id,
                    resource_type=resource_config.resource_type,
                    is_collection=is_collection,
                    use_resource_type_path=use_resource_type_path,
                )
            },
        }

        relationships: dict[str, Any] = {}
        for relationship_name, relationship_config in resource_config.relationships.items():
            relationship_value = item.get(relationship_name)
            relationship_data = self._build_relationship_data(
                relationship_value=relationship_value,
                relationship_config=relationship_config,
            )

            if use_resource_type_path:
                relationship_base = f"/{resource_config.resource_type}/{item_id}/"
            else:
                relationship_base = self._build_item_path(request.path, item_id) if is_collection else request.path
            relationship_base = relationship_base.rstrip("/")
            relationships[relationship_name] = {
                "data": relationship_data,
                "links": {
                    "self": request.build_absolute_uri(relationship_base + f"/relationships/{relationship_name}/"),
                    "related": request.build_absolute_uri(relationship_base + f"/{relationship_name}/"),
                },
            }

        if relationships:
            response_item["relationships"] = relationships

        return response_item

    @classmethod
    def _build_relationship_data(
        cls,
        *,
        relationship_value: Any,
        relationship_config: JSONAPIRelationshipConfig,
    ) -> Any:
        if relationship_config.many:
            if relationship_value is None:
                return []

            if not isinstance(relationship_value, list):
                msg = "JSON:API relationship configured as many expects a list value"
                raise TypeError(msg)

            return [
                cls._relationship_identifier(value=item, relationship_config=relationship_config)
                for item in relationship_value
            ]

        if relationship_value is None:
            return None

        return cls._relationship_identifier(value=relationship_value, relationship_config=relationship_config)

    @classmethod
    def _relationship_identifier(
        cls,
        *,
        value: Any,
        relationship_config: JSONAPIRelationshipConfig,
    ) -> dict[str, str]:
        if not isinstance(value, dict):
            msg = "JSON:API relationship value must be a dict containing the relationship id"
            raise TypeError(msg)

        rel_id = value.get(relationship_config.id_field)
        if rel_id is None:
            msg = f"JSON:API relationship value is missing id field. Expected field {relationship_config.id_field!r}."
            raise ValueError(msg)

        return {
            "id": str(rel_id),
            "type": relationship_config.resource_type,
        }

    @staticmethod
    def _build_item_path(request_path: str, item_id: str) -> str:
        base_path = request_path if request_path.endswith("/") else f"{request_path}/"
        return f"{base_path}{item_id}/"

    def _build_item_self_link(
        self,
        *,
        request,
        item_id: str,
        resource_type: str,
        is_collection: bool,
        use_resource_type_path: bool,
    ) -> str:
        if use_resource_type_path:
            return request.build_absolute_uri(f"/{resource_type}/{item_id}/")

        request_path = request.path
        if is_collection:
            item_path = self._build_item_path(request_path, item_id)
        else:
            item_path = request_path if request_path.endswith("/") else f"{request_path}/"

        return request.build_absolute_uri(item_path)

    @staticmethod
    def _coerce_to_dict(item: Any) -> dict[str, Any]:
        if isinstance(item, dict):
            return item

        try:
            from pydantic import BaseModel as PydanticBaseModel

            if isinstance(item, PydanticBaseModel):
                return item.model_dump()
        except ImportError:  # pragma: no cover
            pass

        try:
            from django.db import models as django_models

            if isinstance(item, django_models.Model):
                data: dict[str, Any] = {}
                for field in item._meta.get_fields():
                    if not hasattr(field, "attname"):
                        continue
                    if isinstance(field, django_models.ForeignKey):
                        # Store FK as {"id": value} so it's compatible with
                        # JSON:API relationship handling.
                        fk_val = getattr(item, field.attname, None)
                        data[field.name] = {"id": fk_val} if fk_val is not None else None
                    else:
                        data[field.attname] = getattr(item, field.attname, None)
                return data
        except ImportError:  # pragma: no cover
            pass

        msg = (
            "JSON:API renderer expects endpoint response to be a dict, list of dicts, "
            "Pydantic BaseModel, or Django Model instance"
        )
        raise TypeError(msg)

    @staticmethod
    def _is_jsonapi_document(data: Any) -> bool:
        if not isinstance(data, dict):
            return False

        return "data" in data or "errors" in data or "jsonapi" in data
