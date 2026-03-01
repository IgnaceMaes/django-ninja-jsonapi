from __future__ import annotations

import math
from typing import Any, Optional
from urllib.parse import urlencode

from django.http import HttpRequest

from django_ninja_jsonapi.renderers import (
    REQUEST_JSONAPI_INCLUDED_ATTR,
    REQUEST_JSONAPI_LINKS_ATTR,
    REQUEST_JSONAPI_META_ATTR,
    JSONAPIIncludedEntry,
    JSONAPIRelationshipConfig,
    JSONAPIResourceConfig,
    normalize_relationships,
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
        relationships=normalize_relationships(relationships),
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





# ---------------------------------------------------------------------------
# Pagination helpers
# ---------------------------------------------------------------------------


def _build_page_url(request: HttpRequest, page_params: dict[str, str]) -> str:
    """Build a full URL preserving existing query params but replacing page params."""
    current_params = dict(request.GET.lists())
    merged: dict[str, str | list[str]] = {}
    for key, values in current_params.items():
        if key.startswith("page["):
            continue
        merged[key] = values[-1] if len(values) == 1 else values
    merged.update(page_params)
    qs = urlencode(merged, doseq=True)
    # JSON:API convention: keep brackets unencoded in query strings
    qs = qs.replace("%5B", "[").replace("%5D", "]")
    base = request.build_absolute_uri(request.path)
    return f"{base}?{qs}" if qs else base


def jsonapi_pagination(
    request: HttpRequest,
    *,
    count: int,
    page_size: int = 20,
    page_number: int = 1,
) -> None:
    """
    Add JSON:API pagination meta and links to the request.

    Computes ``totalPages`` and builds ``first``, ``last``, ``prev``, ``next``
    links using ``page[number]`` / ``page[size]`` strategy. Calls
    :func:`jsonapi_meta` and :func:`jsonapi_links` internally.

    Example::

        @api.get("/articles", response=jsonapi_response(ArticleSchema, "articles", many=True))
        @jsonapi_resource("articles")
        def list_articles(request):
            qs = Article.objects.all()
            count = qs.count()
            page_number = int(request.GET.get("page[number]", 1))
            page_size = int(request.GET.get("page[size]", 20))
            start = (page_number - 1) * page_size
            items = list(qs[start:start + page_size].values())
            jsonapi_pagination(request, count=count, page_size=page_size, page_number=page_number)
            return items
    """
    total_pages = max(1, math.ceil(count / page_size)) if page_size > 0 else 1

    jsonapi_meta(request, count=count, totalPages=total_pages)

    links: dict[str, str] = {
        "first": _build_page_url(request, {"page[number]": "1", "page[size]": str(page_size)}),
        "last": _build_page_url(request, {"page[number]": str(total_pages), "page[size]": str(page_size)}),
    }

    if page_number > 1:
        links["prev"] = _build_page_url(request, {"page[number]": str(page_number - 1), "page[size]": str(page_size)})

    if page_number < total_pages:
        links["next"] = _build_page_url(request, {"page[number]": str(page_number + 1), "page[size]": str(page_size)})

    jsonapi_links(request, **links)


def jsonapi_cursor_pagination(
    request: HttpRequest,
    *,
    page_size: int = 20,
    next_cursor: Optional[str] = None,
    prev_cursor: Optional[str] = None,
) -> None:
    """
    Add JSON:API cursor-based pagination links to the request.

    Builds ``next`` and ``prev`` links using ``page[cursor]`` / ``page[size]``
    strategy. Unlike :func:`jsonapi_pagination`, this does not set ``count`` or
    ``totalPages`` meta since cursor pagination typically doesn't know totals.

    Example::

        @api.get("/articles", response=jsonapi_response(ArticleSchema, "articles", many=True))
        @jsonapi_resource("articles")
        def list_articles(request):
            cursor = request.GET.get("page[cursor]")
            items, next_cursor, prev_cursor = my_cursor_paginate(cursor, page_size=20)
            jsonapi_cursor_pagination(request, next_cursor=next_cursor, prev_cursor=prev_cursor)
            return items
    """
    links: dict[str, str] = {}

    if next_cursor is not None:
        links["next"] = _build_page_url(request, {"page[cursor]": next_cursor, "page[size]": str(page_size)})

    if prev_cursor is not None:
        links["prev"] = _build_page_url(request, {"page[cursor]": prev_cursor, "page[size]": str(page_size)})

    if links:
        jsonapi_links(request, **links)
