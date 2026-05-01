"""Django Model → Pydantic Schema generator.

Provides ``ModelSchema``, a declarative base class for deriving Pydantic
schemas from Django model definitions::

    from django_ninja_jsonapi import ModelSchema

    class CustomerSchema(ModelSchema):
        class Meta:
            model = Customer
            fields = ["id", "name", "email"]
            resource_type = "customers"

Generated schemas include ``ConfigDict(from_attributes=True)`` and optional
``JsonApiMeta`` for transparent ``NinjaJsonAPI`` integration.
"""

from __future__ import annotations

import datetime
import uuid
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

# Mapping from Django field types to Python types
_DJANGO_FIELD_TYPE_MAP: dict[str, type] = {
    "AutoField": int,
    "BigAutoField": int,
    "SmallAutoField": int,
    "BigIntegerField": int,
    "BooleanField": bool,
    "CharField": str,
    "DateField": datetime.date,
    "DateTimeField": datetime.datetime,
    "DecimalField": Decimal,
    "DurationField": datetime.timedelta,
    "EmailField": str,
    "FileField": str,
    "FilePathField": str,
    "FloatField": float,
    "GenericIPAddressField": str,
    "IPAddressField": str,
    "IntegerField": int,
    "JSONField": Any,
    "NullBooleanField": bool,
    "PositiveBigIntegerField": int,
    "PositiveIntegerField": int,
    "PositiveSmallIntegerField": int,
    "SlugField": str,
    "SmallIntegerField": int,
    "TextField": str,
    "TimeField": datetime.time,
    "URLField": str,
    "UUIDField": uuid.UUID,
    "BinaryField": bytes,
    "ForeignKey": int,
}


def _get_field_type(django_field: Any) -> type:
    """Resolve a Django model field to a Python type."""
    field_class_name = type(django_field).__name__

    if field_class_name == "ForeignKey":
        # For FK fields, use the type of the related model's PK
        related_pk = django_field.related_model._meta.pk
        if related_pk is not None:
            return _get_field_type(related_pk)
        return int

    return _DJANGO_FIELD_TYPE_MAP.get(field_class_name, Any)


def _is_field_nullable(django_field: Any) -> bool:
    """Check if a Django field allows null."""
    return getattr(django_field, "null", False)


def _has_default(django_field: Any) -> bool:
    """Check if a Django field has a default value."""
    from django.db.models.fields import NOT_PROVIDED

    default = getattr(django_field, "default", NOT_PROVIDED)
    return default is not NOT_PROVIDED


# ---------------------------------------------------------------------------
# Shared field resolution
# ---------------------------------------------------------------------------


def _resolve_model_fields(
    model: Any,
    fields: list[str] | None,
    exclude: set[str] | None,
    all_optional: bool,
    optional_fields: set[str] | None,
) -> tuple[list[str], dict[str, Any], dict[str, Any]]:
    """Resolve Django model fields to annotations and defaults.

    Returns:
        A tuple of (field_names, annotations_dict, defaults_dict).
    """
    from django.db import models as django_models

    # Collect Django model fields by name for quick lookup
    django_field_map: dict[str, Any] = {}
    for f in model._meta.get_fields():
        if hasattr(f, "attname"):
            django_field_map[f.name] = f
            if f.attname != f.name:
                django_field_map[f.attname] = f

    # Determine which fields to include
    if fields is not None:
        field_names = list(fields)
    else:
        field_names = [
            f.name
            for f in model._meta.get_fields()
            if hasattr(f, "attname") and not isinstance(f, django_models.ForeignKey)
        ]

    if exclude:
        field_names = [f for f in field_names if f not in exclude]

    annotations: dict[str, Any] = {}
    defaults: dict[str, Any] = {}

    for field_name in field_names:
        django_field = django_field_map.get(field_name)

        if django_field is not None:
            python_type: Any = _get_field_type(django_field)
            nullable = _is_field_nullable(django_field)
            has_def = _has_default(django_field)

            is_optional = all_optional or (optional_fields and field_name in optional_fields) or nullable or has_def

            if is_optional:
                annotations[field_name] = Optional[python_type]
                defaults[field_name] = None
            else:
                annotations[field_name] = python_type
        else:
            hints = getattr(model, "__annotations__", {})
            prop_type: Any = hints.get(field_name, Any)

            if not hasattr(model, field_name) and field_name not in hints:
                msg = f"field {field_name!r} not found as a database field, property, or annotation on {model.__name__}"
                raise ValueError(msg)

            annotations[field_name] = Optional[prop_type]
            defaults[field_name] = None

    return field_names, annotations, defaults


def _attach_jsonapi_meta(schema: type, resource_type: str | None, id_field: str | None) -> None:
    """Attach a ``JsonApiMeta`` instance to *schema* if *resource_type* is set."""
    if resource_type is not None:
        from django_ninja_jsonapi.meta import JsonApiMeta

        schema.jsonapi_meta = JsonApiMeta(resource_type=resource_type, id_field=id_field)  # ty: ignore[unresolved-attribute]


# ---------------------------------------------------------------------------
# Class-based ModelSchema
# ---------------------------------------------------------------------------

_PydanticMetaclass = type(BaseModel)


class _ModelSchemaMeta(_PydanticMetaclass):
    """Metaclass that reads a ``Meta`` inner class to auto-generate fields from a Django model."""

    def __new__(mcs, name: str, bases: tuple[type, ...], namespace: dict[str, Any], **kwargs: Any) -> Any:
        meta = namespace.get("Meta")

        # Only process concrete subclasses that declare Meta.model
        if meta is not None and hasattr(meta, "model"):
            model = meta.model
            fields = getattr(meta, "fields", None)
            exclude = getattr(meta, "exclude", None)
            all_optional = getattr(meta, "all_optional", False)
            optional_fields = getattr(meta, "optional_fields", None)

            _, annotations, defaults = _resolve_model_fields(
                model,
                fields,
                exclude,
                all_optional,
                optional_fields,
            )

            # Inject annotations — user-declared fields take precedence
            existing_annotations = namespace.get("__annotations__", {})
            for field_name, annotation in annotations.items():
                if field_name not in existing_annotations:
                    existing_annotations[field_name] = annotation
                    if field_name in defaults:
                        namespace.setdefault(field_name, defaults[field_name])
            namespace["__annotations__"] = existing_annotations

        cls = super().__new__(mcs, name, bases, namespace, **kwargs)

        # Attach JsonApiMeta after class creation (so it doesn't get treated as a field)
        if meta is not None and hasattr(meta, "model"):
            resource_type = getattr(meta, "resource_type", None)
            id_field = getattr(meta, "id_field", None)
            _attach_jsonapi_meta(cls, resource_type, id_field)

        return cls


class ModelSchema(BaseModel, metaclass=_ModelSchemaMeta):
    """Declarative base class for Django model-backed Pydantic schemas.

    Define a ``Meta`` inner class to configure field generation::

        class CustomerSchema(ModelSchema):
            class Meta:
                model = Customer
                fields = ["id", "name", "email"]
                resource_type = "customers"

    **Meta options:**

    - ``model`` — Django model class (required).
    - ``fields`` — List of field names to include. Supports DB fields and
      ``@property`` names. ``None`` means all concrete model fields.
    - ``exclude`` — Set of field names to exclude.
    - ``resource_type`` — JSON:API type string. When set, attaches
      ``JsonApiMeta`` so the schema works with ``NinjaJsonAPI``.
    - ``id_field`` — Name of the JSON:API id field (default: ``"id"``).
    - ``all_optional`` — Make all fields ``Optional`` (for PATCH schemas).
    - ``optional_fields`` — Set of specific fields to make ``Optional``.

    You can declare extra fields directly on the class body — they are
    merged with the auto-generated fields::

        class CustomerSchema(ModelSchema):
            full_address: str = ""  # extra field not on the model

            class Meta:
                model = Customer
                fields = ["id", "name"]

    User-declared fields always take precedence over auto-generated ones.
    """

    model_config = ConfigDict(from_attributes=True)
