"""Schema-level JSON:API resource configuration.

Attach a ``JsonApiMeta`` instance to any Pydantic schema to declare its
JSON:API resource type, id field, and other options.  ``NinjaJsonAPI`` reads
this metadata to automatically wrap responses and unwrap request bodies.

Example::

    from typing import ClassVar
    from django_ninja_jsonapi import JsonApiMeta

    class ArticleSchema(BaseModel):
        model_config = ConfigDict(from_attributes=True)

        uuid: str
        title: str
        body: str
        author: UserSchema | None = None

        jsonapi_meta: ClassVar[JsonApiMeta] = JsonApiMeta(resource_type="articles", id_field="uuid")
"""

from __future__ import annotations

import re
from typing import Any, Type

from pydantic import BaseModel

from django_ninja_jsonapi.renderers import JSONAPIRelationshipConfig


def _pluralize(word: str) -> str:
    """Naive English pluralisation – covers the common cases."""
    if word.endswith("s") or word.endswith("x") or word.endswith("z"):
        return word + "es"
    if word.endswith("sh") or word.endswith("ch"):
        return word + "es"
    if word.endswith("y") and len(word) > 1 and word[-2] not in "aeiou":
        return word[:-1] + "ies"
    return word + "s"


def _dasherize(name: str) -> str:
    """Convert a CamelCase or snake_case name to dasherized-lowercase.

    ``IntakeConfig`` → ``intake-config``
    ``intake_config`` → ``intake-config``
    """
    # CamelCase → underscore
    s1 = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    s2 = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", s1)
    return s2.replace("_", "-").lower()


class JsonApiMeta:
    """Declarative JSON:API configuration for a Pydantic schema.

    Parameters
    ----------
    resource_type:
        The JSON:API ``type`` string (e.g. ``"articles"``).
        If omitted it is inferred from the schema class name:
        strip ``Schema`` suffix, dasherize, pluralise.
    id_field:
        Name of the schema field that holds the resource ID.
        Defaults to ``"id"`` (or ``"uuid"`` when the schema has a
        ``uuid`` field but no ``id`` field).
    """

    def __init__(
        self,
        *,
        resource_type: str | None = None,
        id_field: str | None = None,
    ) -> None:
        self.resource_type = resource_type
        self.id_field = id_field

    # ---- Resolution (needs the owning schema class) ----

    def resolve_resource_type(self, schema: Type[BaseModel]) -> str:
        """Return the effective resource type for *schema*."""
        if self.resource_type is not None:
            return self.resource_type
        name = schema.__name__
        for suffix in ("Schema", "Create", "Update"):
            name = name.removesuffix(suffix)
        return _pluralize(_dasherize(name))

    def resolve_id_field(self, schema: Type[BaseModel]) -> str:
        """Return the effective id field for *schema*."""
        if self.id_field is not None:
            return self.id_field
        fields = schema.model_fields
        if "id" in fields:
            return "id"
        if "uuid" in fields:
            return "uuid"
        return "id"


# ---------------------------------------------------------------------------
# Default instance (used when a schema has no explicit jsonapi_meta)
# ---------------------------------------------------------------------------

_DEFAULT_META = JsonApiMeta()


def get_jsonapi_meta(schema: Type[BaseModel]) -> JsonApiMeta | None:
    """Return the ``JsonApiMeta`` attached to *schema*, or ``None``."""
    return getattr(schema, "jsonapi_meta", None)


def get_or_default_meta(schema: Type[BaseModel]) -> JsonApiMeta:
    """Return the ``JsonApiMeta`` for *schema*, falling back to defaults."""
    return get_jsonapi_meta(schema) or _DEFAULT_META


# ---------------------------------------------------------------------------
# Auto-relationship detection
# ---------------------------------------------------------------------------


def _is_jsonapi_schema(annotation: Any) -> bool:
    """Return ``True`` if *annotation* is a BaseModel subclass with jsonapi_meta."""
    try:
        return (
            isinstance(annotation, type)
            and issubclass(annotation, BaseModel)
            and hasattr(annotation, "jsonapi_meta")
            and isinstance(annotation.jsonapi_meta, JsonApiMeta)
        )
    except TypeError:
        return False


def _unwrap_optional(annotation: Any) -> Any:
    """Unwrap ``Optional[X]`` / ``X | None`` → ``X``."""
    import types
    import typing

    origin = getattr(annotation, "__origin__", None)
    if origin is typing.Union:
        args = [a for a in typing.get_args(annotation) if a is not type(None)]
        return args[0] if len(args) == 1 else annotation

    # Python 3.10+ PEP 604: X | None
    if isinstance(annotation, types.UnionType):
        args = [a for a in typing.get_args(annotation) if a is not type(None)]
        return args[0] if len(args) == 1 else annotation

    return annotation


def _unwrap_list(annotation: Any) -> tuple[bool, Any]:
    """If *annotation* is ``list[X]``, return ``(True, X)`` else ``(False, annotation)``."""
    origin = getattr(annotation, "__origin__", None)
    if origin is list:
        import typing

        args = typing.get_args(annotation)
        return (True, args[0]) if args else (False, annotation)
    return False, annotation


def detect_relationships(schema: Type[BaseModel]) -> dict[str, JSONAPIRelationshipConfig]:
    """Auto-detect JSON:API relationships from schema field types.

    A field is a relationship if its (unwrapped) type is a ``BaseModel``
    subclass that carries a ``jsonapi_meta`` attribute.
    """
    relationships: dict[str, JSONAPIRelationshipConfig] = {}

    for field_name, field_info in schema.model_fields.items():
        annotation = field_info.annotation
        if annotation is None:
            continue

        # Unwrap Optional
        inner = _unwrap_optional(annotation)

        # Check list[X]
        is_many, inner = _unwrap_list(inner)

        # Unwrap Optional inside list (list[Optional[X]])
        if is_many:
            inner = _unwrap_optional(inner)

        if _is_jsonapi_schema(inner):
            meta = get_or_default_meta(inner)
            relationships[field_name] = JSONAPIRelationshipConfig(
                resource_type=meta.resolve_resource_type(inner),
                many=is_many,
                id_field=meta.resolve_id_field(inner),
            )

    return relationships
