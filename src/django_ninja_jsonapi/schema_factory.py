"""
Standalone JSON:API schema factories for OpenAPI documentation and input parsing.

Generate Pydantic models that represent JSON:API document structures so that:
- ``response=jsonapi_response(MySchema, "articles")`` produces correct OpenAPI docs
- ``body: jsonapi_body(MySchema, "articles")`` parses incoming JSON:API request bodies
"""

from __future__ import annotations

from typing import Any, Literal, Optional, Type

from pydantic import BaseModel, ConfigDict, Field, create_model

from django_ninja_jsonapi.renderers import JSONAPIRelationshipConfig, normalize_relationships

_RESPONSE_CACHE: dict[str, Type[BaseModel]] = {}
_BODY_CACHE: dict[str, Type[BaseModel]] = {}


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
        type=(Literal[rel_config.resource_type], rel_config.resource_type),  # type: ignore[valid-type]
    )


def _build_relationship_fields(
    relationships: dict[str, JSONAPIRelationshipConfig],
) -> dict[str, tuple[type, Any]]:
    """Build pydantic field definitions for each relationship."""
    fields: dict[str, tuple[type, Any]] = {}

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
                data=(identifier, ...),
                links=(Optional[RelationshipLinks], None),
            )

        fields[rel_name] = (Optional[data_model], None)

    return fields


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
    attr_fields: dict[str, tuple[type, Any]] = {}
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
    resource_object_fields: dict[str, tuple[type, Any]] = {
        "id": (str, Field(description="Resource object ID", examples=["1"])),
        "type": (Literal[resource_type], Field(default=resource_type, description="Resource type")),  # type: ignore[valid-type]
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
        meta_model = None  # type: ignore[assignment]

    # --- top-level document ---
    doc_fields: dict[str, tuple[type, Any]] = {}

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

    document_model = create_model(
        f"{schema_name}JsonApiResponse" if not many else f"{schema_name}JsonApiListResponse",
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
) -> Type[BaseModel]:
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
    data_fields: dict[str, tuple[type, Any]] = {
        "type": (Literal[resource_type], Field(default=resource_type, description="Resource type")),  # type: ignore[valid-type]
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

    data_item_model = create_model(
        f"{schema_name}DataIn",
        __config__=ConfigDict(extra="forbid"),
        **data_fields,
    )

    # --- top-level wrapper ---
    body_model = create_model(
        f"{schema_name}JsonApiBody",
        __config__=ConfigDict(extra="forbid"),
        data=(data_item_model, Field(description="JSON:API data")),
    )

    _BODY_CACHE[key] = body_model
    return body_model
