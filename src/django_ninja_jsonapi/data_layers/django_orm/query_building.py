from __future__ import annotations

from typing import Any

from django.db.models import Q, QuerySet


def _normalize_lookup(field_name: str) -> str:
    return field_name.replace(".", "__")


def _build_condition_q(item: dict[str, Any]) -> Q:
    if "and" in item:
        q = Q()
        for child in item["and"]:
            q &= _build_condition_q(child)
        return q

    if "or" in item:
        q = Q()
        children = item["or"]
        if not children:
            return q

        q = _build_condition_q(children[0])
        for child in children[1:]:
            q |= _build_condition_q(child)
        return q

    if "not" in item:
        return ~_build_condition_q(item["not"])

    field_name = _normalize_lookup(item["name"])
    op = item.get("op", "eq")
    value = item.get("val")

    if op == "eq":
        return Q(**{field_name: value})
    if op == "ne":
        return ~Q(**{field_name: value})
    if op == "lt":
        return Q(**{f"{field_name}__lt": value})
    if op == "le":
        return Q(**{f"{field_name}__lte": value})
    if op == "gt":
        return Q(**{f"{field_name}__gt": value})
    if op == "ge":
        return Q(**{f"{field_name}__gte": value})
    if op == "in":
        values = value if isinstance(value, list) else [value]
        return Q(**{f"{field_name}__in": values})
    if op == "not_in":
        values = value if isinstance(value, list) else [value]
        return ~Q(**{f"{field_name}__in": values})
    if op == "like":
        return Q(**{f"{field_name}__contains": value})
    if op == "ilike":
        return Q(**{f"{field_name}__icontains": value})
    if op == "is_null":
        return Q(**{f"{field_name}__isnull": bool(value)})

    return Q()


def apply_filters(queryset: QuerySet, filters: list[dict[str, Any]]) -> QuerySet:
    for item in filters:
        queryset = queryset.filter(_build_condition_q(item))

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
