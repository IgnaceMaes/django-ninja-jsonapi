"""Django Model → Pydantic Schema generator.

Provides ``model_schema()`` to automatically generate Pydantic ``BaseModel``
subclasses from Django model definitions, including support for
``@property`` fields, ``all_optional`` (PATCH semantics), and
``from_attributes`` configuration.

Example::

    from django_ninja_jsonapi import model_schema

    IntakeConfigSchema = model_schema(
        IntakeConfig,
        fields=["uuid", "name", "is_active", "organization_name", "created_dt"],
        id_field="uuid",
    )

    IntakeConfigUpdateSchema = model_schema(
        IntakeConfig,
        fields=["name", "is_active"],
        all_optional=True,
    )
"""

from __future__ import annotations

import datetime
import uuid
from decimal import Decimal
from typing import Any, Optional, Type

from pydantic import BaseModel, ConfigDict, create_model

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


def model_schema(
    model: Any,
    *,
    fields: list[str] | None = None,
    exclude: set[str] | None = None,
    id_field: str | None = None,
    optional_fields: set[str] | None = None,
    all_optional: bool = False,
    name: str | None = None,
    extra_fields: dict[str, tuple[type, Any]] | None = None,
) -> Type[BaseModel]:
    """Generate a Pydantic schema from a Django model.

    Args:
        model: A Django model class.
        fields: List of field names to include.  Supports both database fields
            and ``@property`` names.  If ``None``, all concrete model fields
            are included.
        exclude: Set of field names to exclude (applied after *fields*).
        id_field: Name of the field used as the JSON:API ``id``.  When set,
            this field is always included and named ``id`` in the schema
            (unless the field is already named ``id``).
        optional_fields: Set of fields to mark as ``Optional`` regardless of
            the model definition.
        all_optional: If ``True``, **all** fields become ``Optional`` —
            useful for PATCH/update schemas.
        name: Custom name for the generated model.  Defaults to
            ``{ModelName}Schema``.
        extra_fields: Additional Pydantic field definitions to include in
            the schema, as ``{name: (type, default_or_Field)}``.

    Returns:
        A Pydantic ``BaseModel`` subclass.
    """
    from django.db import models as django_models

    model_name = name or f"{model.__name__}Schema"

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

    # Build pydantic field definitions
    pydantic_fields: dict[str, tuple[Any, Any]] = {}

    for field_name in field_names:
        django_field = django_field_map.get(field_name)

        if django_field is not None:
            # Known Django model field
            python_type = _get_field_type(django_field)
            nullable = _is_field_nullable(django_field)
            has_def = _has_default(django_field)

            is_optional = all_optional or (optional_fields and field_name in optional_fields) or nullable or has_def

            if is_optional:
                pydantic_fields[field_name] = (Optional[python_type], None)  # ty: ignore[invalid-type-form]
            else:
                pydantic_fields[field_name] = (python_type, ...)
        else:
            # Not a database field — assume it's a @property or annotation.
            # Try to get a type hint from the model class.
            hints = getattr(model, "__annotations__", {})
            prop_type = hints.get(field_name, Any)

            # Check if it's actually a property on the model
            if not hasattr(model, field_name) and field_name not in hints:
                msg = (
                    f"model_schema: field {field_name!r} not found as a database field, "
                    f"property, or annotation on {model.__name__}"
                )
                raise ValueError(msg)

            if all_optional or (optional_fields and field_name in optional_fields):
                pydantic_fields[field_name] = (Optional[prop_type], None)
            else:
                pydantic_fields[field_name] = (Optional[prop_type], None)

    # Merge extra fields
    if extra_fields:
        pydantic_fields.update(extra_fields)

    schema = create_model(  # ty: ignore[no-matching-overload]
        model_name,
        __config__=ConfigDict(from_attributes=True),
        **pydantic_fields,
    )

    return schema
