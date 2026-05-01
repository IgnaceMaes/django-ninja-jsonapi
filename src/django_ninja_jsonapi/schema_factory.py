"""
Standalone JSON:API schema factories for OpenAPI documentation and input parsing.

Generate Pydantic models that represent JSON:API document structures so that:
- ``response=jsonapi_response(MySchema, "articles")`` produces correct OpenAPI docs
- ``body: jsonapi_body(MySchema, "articles")`` parses incoming JSON:API request bodies
"""

from __future__ import annotations

from typing import Any, Generic, Literal, Optional, Type, TypeVar

from pydantic import BaseModel, ConfigDict, Field, create_model, model_validator

from django_ninja_jsonapi.renderers import JSONAPIRelationshipConfig, normalize_relationships

_RESPONSE_CACHE: dict[str, Type[BaseModel]] = {}
_BODY_CACHE: dict[str, Type[Any]] = {}

# ---------------------------------------------------------------------------
# Generic base classes for type-checker / IDE support
# ---------------------------------------------------------------------------

TAttributes = TypeVar("TAttributes", bound=BaseModel)


class JsonApiRelationships(BaseModel):
    """Base class for relationships — extended dynamically by ``jsonapi_body()``."""


class JsonApiDataIn(BaseModel, Generic[TAttributes]):
    """Typed wrapper around the ``data`` field of a JSON:API body.

    Provides ``get_rel_id`` and ``get_rel_ids`` for convenient relationship
    access.  The actual class used at runtime is a ``create_model()`` subclass;
    this generic exists so that type checkers can infer ``.attributes`` as
    ``TAttributes``.
    """

    type: str = ""
    attributes: TAttributes

    def get_rel_id(self, name: str) -> str | None:
        """Get the ID of a to-one relationship by name, or ``None``."""
        rels = getattr(self, "relationships", None)
        if rels is None:
            return None
        rel = getattr(rels, name, None)
        if rel is None or rel.data is None:
            return None
        return rel.data.id

    def get_rel_ids(self, name: str) -> list[str]:
        """Get the IDs of a to-many relationship by name."""
        rels = getattr(self, "relationships", None)
        if rels is None:
            return []
        rel = getattr(rels, name, None)
        if rel is None or rel.data is None:
            return []
        return [item.id for item in rel.data]


class JsonApiBody(BaseModel, Generic[TAttributes]):
    """Typed wrapper around a JSON:API request body.

    Use as a type annotation with a type parameter for full IDE support::

        body: JsonApiBody[ArticleCreateSchema]
        body.data.attributes.title  # ← autocomplete works

    At runtime the actual class is still built by ``jsonapi_body()``, but this
    generic provides the type information that checkers and IDEs need.
    """

    data: JsonApiDataIn[TAttributes]

    def get_rel_id(self, name: str) -> str | None:
        """Shortcut: delegates to ``self.data.get_rel_id(name)``."""
        return self.data.get_rel_id(name)

    def get_rel_ids(self, name: str) -> list[str]:
        """Shortcut: delegates to ``self.data.get_rel_ids(name)``."""
        return self.data.get_rel_ids(name)


# ---------------------------------------------------------------------------
# Shared models for well-typed links / included / jsonapi version
# ---------------------------------------------------------------------------


class JsonApiVersionObject(BaseModel):
    """Top-level ``jsonapi`` key."""

    version: str = Field(default="1.0", examples=["1.0"])


class ResourceLinks(BaseModel):
    """Links object on a resource object."""

    model_config = ConfigDict(extra="allow")

    self: Optional[str] = Field(default=None, examples=["http://example.com/articles/1/"])


class DocumentLinks(BaseModel):
    """Top-level document links (always includes ``self``, may include pagination)."""

    model_config = ConfigDict(extra="allow")

    self: Optional[str] = Field(default=None, examples=["http://example.com/articles/"])
    first: Optional[str] = Field(default=None, examples=["http://example.com/articles/?page[number]=1"])
    last: Optional[str] = Field(default=None, examples=["http://example.com/articles/?page[number]=5"])
    prev: Optional[str] = Field(default=None, examples=[None])
    next: Optional[str] = Field(default=None, examples=["http://example.com/articles/?page[number]=2"])


class RelationshipLinks(BaseModel):
    """Links inside a relationship object."""

    model_config = ConfigDict(extra="allow")

    self: Optional[str] = Field(default=None, examples=["http://example.com/articles/1/relationships/author/"])
    related: Optional[str] = Field(default=None, examples=["http://example.com/articles/1/author/"])


class IncludedResourceObject(BaseModel):
    """A resource object inside the ``included`` array."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(examples=["1"])
    type: str = Field(examples=["people"])
    attributes: Optional[dict[str, Any]] = None
    links: Optional[ResourceLinks] = None


def _cache_key(
    schema: Type[BaseModel],
    resource_type: str,
    *,
    many: bool = False,
    relationships: dict[str, JSONAPIRelationshipConfig] | None = None,
    suffix: str = "",
) -> str:
    rel_repr = ""
    if relationships:
        parts = sorted(f"{k}:{v.resource_type}:{v.many}:{v.id_field}" for k, v in relationships.items())
        rel_repr = "|".join(parts)
    return f"{schema.__module__}.{schema.__qualname__}:{resource_type}:{many}:{rel_repr}:{suffix}"


def _build_relationship_identifier_model(rel_config: JSONAPIRelationshipConfig) -> Type[BaseModel]:
    """Build a model for ``{"id": "...", "type": "..."}``."""
    return create_model(
        f"{rel_config.resource_type.title().replace('-', '')}RelIdentifier",
        __config__=ConfigDict(extra="forbid"),
        id=(str, ...),
        type=(Literal[rel_config.resource_type], rel_config.resource_type),
    )


def _build_relationship_fields(
    relationships: dict[str, JSONAPIRelationshipConfig],
) -> dict[str, tuple[Any, Any]]:
    """Build pydantic field definitions for each relationship."""
    fields: dict[str, tuple[Any, Any]] = {}

    for rel_name, rel_config in relationships.items():
        identifier = _build_relationship_identifier_model(rel_config)

        if rel_config.many:
            data_model = create_model(
                f"{rel_name.title().replace('-', '')}RelToMany",
                data=(list[identifier], ...),
                links=(Optional[RelationshipLinks], None),
            )
        else:
            data_model = create_model(
                f"{rel_name.title().replace('-', '')}RelToOne",
                data=(Optional[identifier], None),
                links=(Optional[RelationshipLinks], None),
            )

        fields[rel_name] = (Optional[data_model], None)

    return fields


# ---------------------------------------------------------------------------
# Raw-data coercion: lets jsonapi_response() models accept raw endpoint data
# ---------------------------------------------------------------------------


def _coerce_item_to_dict(item: Any) -> dict[str, Any] | None:
    """Coerce a single item (dict, Pydantic model) to a plain dict."""
    if isinstance(item, dict):
        return item
    try:
        from pydantic import BaseModel as _PBM

        if isinstance(item, _PBM):
            return item.model_dump()
    except ImportError:  # pragma: no cover
        pass
    return None


def _wrap_resource(
    item: dict[str, Any],
    *,
    resource_type: str,
    rels: dict[str, JSONAPIRelationshipConfig],
) -> dict[str, Any]:
    """Wrap a flat dict into a JSON:API resource object structure."""
    rel_keys = set(rels.keys())
    attrs = {k: v for k, v in item.items() if k != "id" and k not in rel_keys}
    resource: dict[str, Any] = {
        "id": str(item.get("id", "")),
        "type": resource_type,
        "attributes": attrs,
    }

    if rels:
        relationships: dict[str, Any] = {}
        for rel_name, rel_config in rels.items():
            value = item.get(rel_name)
            if rel_config.many:
                if value is None or (isinstance(value, list) and len(value) == 0):
                    relationships[rel_name] = {"data": []}
                elif isinstance(value, list):
                    relationships[rel_name] = {
                        "data": [
                            {"id": str(v.get(rel_config.id_field, "")), "type": rel_config.resource_type}
                            if isinstance(v, dict)
                            else {"id": str(v), "type": rel_config.resource_type}
                            for v in value
                        ]
                    }
            else:
                if value is None:
                    relationships[rel_name] = {"data": None}
                elif isinstance(value, dict):
                    relationships[rel_name] = {
                        "data": {
                            "id": str(value.get(rel_config.id_field, "")),
                            "type": rel_config.resource_type,
                        }
                    }
                else:
                    relationships[rel_name] = {"data": {"id": str(value), "type": rel_config.resource_type}}
        resource["relationships"] = relationships

    return resource


def _coerce_raw_to_document(
    data: Any,
    *,
    resource_type: str,
    many: bool,
    rels: dict[str, JSONAPIRelationshipConfig],
) -> Any:
    """Convert raw endpoint return values to a JSON:API document dict.

    Already-valid JSON:API documents (containing ``data``, ``errors`` or
    ``jsonapi`` top-level keys) are returned unchanged.
    """
    # Already a JSON:API document — pass through
    if isinstance(data, dict) and ("data" in data or "errors" in data or "jsonapi" in data):
        return data

    # Single item (dict or Pydantic model) for a detail endpoint
    coerced = _coerce_item_to_dict(data)
    if coerced is not None and not many:
        return {"data": _wrap_resource(coerced, resource_type=resource_type, rels=rels)}

    # Collection endpoint
    if isinstance(data, list) and many:
        resources = []
        for item in data:
            as_dict = _coerce_item_to_dict(item)
            if as_dict is not None:
                resources.append(_wrap_resource(as_dict, resource_type=resource_type, rels=rels))
        return {"data": resources}

    # Single item returned for a many=True schema (wrap into list)
    if coerced is not None and many:
        return {"data": [_wrap_resource(coerced, resource_type=resource_type, rels=rels)]}

    return data


# ---------------------------------------------------------------------------
# jsonapi_response – generates a response schema for OpenAPI docs
# ---------------------------------------------------------------------------


def jsonapi_response(
    schema: Type[BaseModel],
    resource_type: str,
    *,
    many: bool = False,
    relationships: dict[str, JSONAPIRelationshipConfig | dict[str, Any]] | None = None,
) -> Type[BaseModel]:
    """
    Build a Pydantic model representing a JSON:API response document.

    Use as ``response=`` in a Django Ninja endpoint decorator::

        @api.get("/articles", response=jsonapi_response(ArticleSchema, "articles", many=True))
        @jsonapi_resource("articles")
        def list_articles(request):
            ...

    The generated model mirrors the JSON:API top-level document structure
    (``data``, ``links``, ``jsonapi``, ``meta``, ``included``) so that
    OpenAPI / Swagger UI shows the correct response shape.
    """
    rels = normalize_relationships(relationships)
    key = _cache_key(schema, resource_type, many=many, relationships=rels, suffix="response")
    if key in _RESPONSE_CACHE:
        return _RESPONSE_CACHE[key]

    # --- attributes schema (strip id and relationship keys) ---
    attr_fields: dict[str, Any] = {}
    rel_keys = set(rels.keys())
    for field_name, field_info in schema.model_fields.items():
        if field_name == "id" or field_name in rel_keys:
            continue
        attr_fields[field_name] = (field_info.annotation, field_info)

    schema_name = schema.__name__.removesuffix("Schema")
    attributes_model = create_model(
        f"{schema_name}Attributes",
        **attr_fields,
    )

    # --- relationships model (optional) ---
    rel_field_defs = _build_relationship_fields(rels) if rels else {}

    # --- resource object ---
    resource_object_fields: dict[str, Any] = {
        "id": (str, Field(description="Resource object ID", examples=["1"])),
        "type": (Literal[resource_type], Field(default=resource_type, description="Resource type")),
        "attributes": (attributes_model, Field(description="Resource object attributes")),
        "links": (Optional[ResourceLinks], Field(default=None, description="Resource links")),
    }

    if rel_field_defs:
        relationships_model = create_model(
            f"{schema_name}Relationships",
            **rel_field_defs,
        )
        resource_object_fields["relationships"] = (
            Optional[relationships_model],
            Field(default=None, description="Resource relationships"),
        )

    resource_object_model = create_model(
        f"{schema_name}ResourceObject",
        **resource_object_fields,
    )

    # --- meta ---
    if many:
        meta_model = create_model(
            f"{schema_name}ListMeta",
            count=(Optional[int], Field(default=None, examples=[100])),
            totalPages=(Optional[int], Field(default=None, alias="totalPages", examples=[5])),
        )
    else:
        meta_model = None

    # --- top-level document ---
    doc_fields: dict[str, Any] = {}

    if many:
        doc_fields["data"] = (list[resource_object_model], Field(description="Resource objects collection"))
        doc_fields["links"] = (Optional[DocumentLinks], Field(default=None, description="Top level document links"))
        doc_fields["meta"] = (Optional[meta_model], Field(default=None, description="JSON:API metadata"))
    else:
        doc_fields["data"] = (resource_object_model, Field(description="Resource object data"))
        doc_fields["links"] = (Optional[ResourceLinks], Field(default=None, description="Top level document links"))
        doc_fields["meta"] = (Optional[dict[str, Any]], Field(default=None, description="JSON:API metadata"))

    doc_fields["jsonapi"] = (
        Optional[JsonApiVersionObject],
        Field(default=None, description="JSON:API version object"),
    )
    doc_fields["included"] = (
        Optional[list[IncludedResourceObject]],
        Field(default=None, description="Included related resources"),
    )

    # Build a base class with a validator that accepts raw endpoint data
    # (dict / list / Pydantic model) and wraps it into JSON:API structure so
    # Django Ninja's response validation succeeds.  The renderer already
    # detects pre-wrapped documents via ``_is_jsonapi_document`` and passes
    # them through unchanged.
    _rt = resource_type
    _many = many
    _rels = rels

    class _DocumentBase(BaseModel):
        @model_validator(mode="before")
        @classmethod
        def _accept_raw_data(cls, data: Any) -> Any:  # noqa: N805
            return _coerce_raw_to_document(data, resource_type=_rt, many=_many, rels=_rels)

    document_model = create_model(
        f"{schema_name}JsonApiResponse" if not many else f"{schema_name}JsonApiListResponse",
        __base__=_DocumentBase,
        **doc_fields,
    )

    _RESPONSE_CACHE[key] = document_model
    return document_model


# ---------------------------------------------------------------------------
# jsonapi_body – generates an input schema for parsing JSON:API request bodies
# ---------------------------------------------------------------------------


def jsonapi_body(
    schema: Type[BaseModel],
    resource_type: str,
    *,
    relationships: dict[str, JSONAPIRelationshipConfig | dict[str, Any]] | None = None,
    allow_id: bool = False,
) -> Type[JsonApiBody[Any]]:
    """
    Build a Pydantic model representing a JSON:API request body.

    Use as a type annotation in a Django Ninja endpoint::

        @api.post("/articles", response=jsonapi_response(ArticleSchema, "articles"))
        @jsonapi_resource("articles")
        def create_article(request, body: jsonapi_body(ArticleCreateSchema, "articles")):
            attrs = body.data.attributes.model_dump()
            ...

    The generated model expects the JSON:API input document structure::

        {
            "data": {
                "type": "articles",
                "attributes": { ... },
                "relationships": { ... }
            }
        }
    """
    rels = normalize_relationships(relationships)
    key = _cache_key(schema, resource_type, relationships=rels, suffix=f"body:allow_id={allow_id}")
    if key in _BODY_CACHE:
        return _BODY_CACHE[key]

    schema_name = schema.__name__.removesuffix("Schema")

    # --- relationship fields for input ---
    rel_field_defs = _build_relationship_fields(rels) if rels else {}

    # --- data item ---
    data_fields: dict[str, Any] = {
        "type": (Literal[resource_type], Field(default=resource_type, description="Resource type")),
        "attributes": (schema, Field(description="Resource object attributes")),
    }

    if allow_id:
        data_fields["id"] = (Optional[str], Field(default=None, description="Resource object ID"))

    if rel_field_defs:
        relationships_model = create_model(
            f"{schema_name}InRelationships",
            **rel_field_defs,
        )
        data_fields["relationships"] = (
            Optional[relationships_model],
            Field(default=None, description="Resource relationships"),
        )

    # Build the DataIn model using the generic base for type-checker support
    data_item_model = create_model(
        f"{schema_name}DataIn",
        __base__=JsonApiDataIn,
        __config__=ConfigDict(extra="forbid"),
        **data_fields,
    )

    # --- top-level wrapper ---
    body_model = create_model(
        f"{schema_name}JsonApiBody",
        __base__=JsonApiBody,
        __config__=ConfigDict(extra="forbid"),
        data=(data_item_model, Field(description="JSON:API data")),
    )

    _BODY_CACHE[key] = body_model
    return body_model
