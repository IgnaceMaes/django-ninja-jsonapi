from django.test import RequestFactory

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
