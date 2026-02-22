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
