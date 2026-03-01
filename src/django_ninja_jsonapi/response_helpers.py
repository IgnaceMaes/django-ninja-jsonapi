from __future__ import annotations

import math
from typing import Any, Optional, Sequence, TypeVar, Union
from urllib.parse import urlencode

from django.conf import settings
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

T = TypeVar("T")


def _get_jsonapi_config() -> dict[str, Any]:
    """Read the NINJA_JSONAPI config dict from Django settings."""
    return getattr(settings, "NINJA_JSONAPI", {})


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
# High-level pagination (inspired by DRF JSON:API)
# ---------------------------------------------------------------------------


def jsonapi_paginate(
    request: HttpRequest,
    items: Union[Any, Sequence[T]],
    *,
    page_size: int | None = None,
    max_page_size: int | None = None,
) -> list[T]:
    """Paginate a queryset or list and set JSON:API pagination meta + links.

    Reads ``page[number]`` and ``page[size]`` from query parameters (falling
    back to *page_size* or the ``NINJA_JSONAPI["MAX_PAGE_SIZE"]`` setting).
    Counts, slices, sets ``meta`` (``count``, ``totalPages``) and ``links``
    (``first``, ``last``, ``prev``, ``next``) on the request, and returns the
    page of items.

    This is the recommended way to paginate list endpoints — it mirrors how
    DRF JSON:API handles pagination automatically::

        @api.get("/articles", response=list[ArticleSchema])
        @jsonapi_resource("articles")
        def list_articles(request):
            return jsonapi_paginate(request, Article.objects.order_by("id"))

    Items can be a Django ``QuerySet``, a plain ``list``, or any sliceable
    sequence.  Django model instances in the returned list are auto-serialized
    by the renderer.

    Args:
        request: The current HTTP request.
        items: A Django ``QuerySet`` or any sliceable sequence.
        page_size: Default page size when the client doesn't send
            ``page[size]``.  Falls back to ``NINJA_JSONAPI["MAX_PAGE_SIZE"]``
            (default 20).
        max_page_size: Upper bound for client-requested ``page[size]``.
            Falls back to ``NINJA_JSONAPI["MAX_PAGE_SIZE"]`` (default 100).

    Returns:
        A ``list`` containing the items for the requested page.
    """
    config = _get_jsonapi_config()

    # ---- resolve effective page_size ----
    default_size = page_size if page_size is not None else config.get("DEFAULT_PAGE_SIZE", 20)
    effective_max = max_page_size if max_page_size is not None else config.get("MAX_PAGE_SIZE", 100)

    requested = request.GET.get("page[size]")
    if requested is not None:
        effective_size = int(requested)
    else:
        effective_size = default_size

    if effective_max and effective_size > effective_max:
        effective_size = effective_max

    # ---- resolve page number ----
    page_number = int(request.GET.get("page[number]", 1))
    if page_number < 1:
        page_number = 1

    # ---- count ----
    try:
        from django.db.models import QuerySet

        is_queryset = isinstance(items, QuerySet)
    except ImportError:  # pragma: no cover
        is_queryset = False

    if is_queryset:
        count = items.count()  # QuerySet.count() — avoids loading all rows
    else:
        count = len(items)

    # ---- slice ----
    start = (page_number - 1) * effective_size
    page_items = items[start : start + effective_size]
    if not isinstance(page_items, list):
        page_items = list(page_items)

    # ---- set JSON:API pagination meta + links ----
    jsonapi_pagination(
        request,
        count=count,
        page_size=effective_size,
        page_number=page_number,
    )

    return page_items


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
