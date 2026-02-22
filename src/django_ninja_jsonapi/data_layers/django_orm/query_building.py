from __future__ import annotations

from typing import Any

from django.db.models import QuerySet


def _normalize_lookup(field_name: str) -> str:
    return field_name.replace(".", "__")


def apply_filters(queryset: QuerySet, filters: list[dict[str, Any]]) -> QuerySet:
    for item in filters:
        field_name = _normalize_lookup(item["name"])
        op = item.get("op", "eq")
        value = item.get("val")

        if op == "eq":
            queryset = queryset.filter(**{field_name: value})
        elif op == "ne":
            queryset = queryset.exclude(**{field_name: value})
        elif op == "lt":
            queryset = queryset.filter(**{f"{field_name}__lt": value})
        elif op == "le":
            queryset = queryset.filter(**{f"{field_name}__lte": value})
        elif op == "gt":
            queryset = queryset.filter(**{f"{field_name}__gt": value})
        elif op == "ge":
            queryset = queryset.filter(**{f"{field_name}__gte": value})
        elif op == "in":
            values = value if isinstance(value, list) else [value]
            queryset = queryset.filter(**{f"{field_name}__in": values})
        elif op == "not_in":
            values = value if isinstance(value, list) else [value]
            queryset = queryset.exclude(**{f"{field_name}__in": values})
        elif op == "like":
            queryset = queryset.filter(**{f"{field_name}__contains": value})
        elif op == "ilike":
            queryset = queryset.filter(**{f"{field_name}__icontains": value})
        elif op == "is_null":
            queryset = queryset.filter(**{f"{field_name}__isnull": bool(value)})

    return queryset


def apply_sorts(queryset: QuerySet, sorts: list[dict[str, Any]]) -> QuerySet:
    if not sorts:
        return queryset

    order_by: list[str] = []
    for item in sorts:
        field_name = _normalize_lookup(item["field"])
        if item.get("order", "asc") == "desc":
            field_name = f"-{field_name}"

        order_by.append(field_name)

    return queryset.order_by(*order_by)
