from django.test import RequestFactory

from django_ninja_jsonapi.exceptions import BadRequest
from django_ninja_jsonapi.querystring import QueryStringManager


def test_querystring_filters_and_sorts_parsing():
    request = RequestFactory().get(
        "/api/users",
        {
            "filter[name]": "john",
            "sort": "-created_at,name",
        },
    )

    manager = QueryStringManager(request)

    assert manager.filters == [{"name": "name", "op": "eq", "val": "john"}]
    assert manager.sorts == [
        {"field": "created_at", "order": "desc", "rel_path": None},
        {"field": "name", "order": "asc", "rel_path": None},
    ]


def test_querystring_include_and_pagination_parsing():
    request = RequestFactory().get(
        "/api/users",
        {
            "include": "posts.author",
            "page[number]": "2",
            "page[size]": "10",
        },
    )

    manager = QueryStringManager(request)

    assert manager.include == ["posts.author"]
    assert manager.pagination.number == 2
    assert manager.pagination.size == 10


def test_querystring_cursor_pagination_parsing():
    request = RequestFactory().get(
        "/api/users",
        {
            "page[cursor]": "100",
            "page[size]": "10",
        },
    )

    manager = QueryStringManager(request)

    assert manager.pagination.cursor == "100"
    assert manager.pagination.size == 10


def test_querystring_defaults_page_size_to_twenty_when_not_provided():
    request = RequestFactory().get("/api/users")

    manager = QueryStringManager(request)

    assert manager.pagination.number == 1
    assert manager.pagination.size == 20


def test_querystring_clamps_page_size_to_default_max_when_not_configured():
    request = RequestFactory().get("/api/users", {"page[size]": "999"})

    manager = QueryStringManager(request)

    assert manager.pagination.size == 20


def test_querystring_keeps_limit_offset_strategy_without_page_size():
    request = RequestFactory().get("/api/users", {"page[offset]": "5", "page[limit]": "3"})

    manager = QueryStringManager(request)

    assert manager.pagination.size is None
    assert manager.pagination.offset == 5
    assert manager.pagination.limit == 3


def test_querystring_offset_limit_strategy_clamps_negative_and_defaults_limit():
    request = RequestFactory().get("/api/users", {"page[offset]": "-1", "page[limit]": "-2"})

    manager = QueryStringManager(request)

    assert manager.pagination.size is None
    assert manager.pagination.offset == 0
    assert manager.pagination.limit == 20


def test_querystring_invalid_pagination_value_raises_bad_request():
    request = RequestFactory().get("/api/users", {"page[number]": "not-an-int"})

    try:
        _ = QueryStringManager(request).pagination
        raise AssertionError("Expected BadRequest for invalid pagination parameter")
    except BadRequest as exc:
        assert exc.as_dict["source"] == {"parameter": "page"}


def test_querystring_rejects_unknown_query_param():
    request = RequestFactory().get(
        "/api/users",
        {
            "foo": "bar",
        },
    )

    try:
        QueryStringManager(request)
        raise AssertionError("Expected BadRequest for unknown parameter")
    except BadRequest as exc:
        assert exc.as_dict["source"] == {"parameter": "foo"}


def test_querystring_rejects_repeated_non_filter_param():
    request = RequestFactory().get(
        "/api/users?page[size]=10&page[size]=20",
    )

    try:
        QueryStringManager(request)
        raise AssertionError("Expected BadRequest for repeated page[size]")
    except BadRequest as exc:
        assert exc.as_dict["source"] == {"parameter": "page[size]"}
