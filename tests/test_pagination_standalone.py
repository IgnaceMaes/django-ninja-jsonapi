from django.test import RequestFactory, override_settings

from django_ninja_jsonapi.renderers import REQUEST_JSONAPI_LINKS_ATTR, REQUEST_JSONAPI_META_ATTR
from django_ninja_jsonapi.response_helpers import jsonapi_cursor_pagination, jsonapi_paginate, jsonapi_pagination


class TestJsonapiPagination:
    def test_sets_count_and_total_pages_meta(self):
        request = RequestFactory().get("/articles/")
        jsonapi_pagination(request, count=50, page_size=10, page_number=1)

        meta = getattr(request, REQUEST_JSONAPI_META_ATTR)
        assert meta["count"] == 50
        assert meta["totalPages"] == 5

    def test_total_pages_rounds_up(self):
        request = RequestFactory().get("/articles/")
        jsonapi_pagination(request, count=51, page_size=10, page_number=1)

        meta = getattr(request, REQUEST_JSONAPI_META_ATTR)
        assert meta["totalPages"] == 6

    def test_total_pages_is_at_least_one(self):
        request = RequestFactory().get("/articles/")
        jsonapi_pagination(request, count=0, page_size=10, page_number=1)

        meta = getattr(request, REQUEST_JSONAPI_META_ATTR)
        assert meta["totalPages"] == 1

    def test_first_and_last_links_always_present(self):
        request = RequestFactory().get("/articles/")
        jsonapi_pagination(request, count=100, page_size=20, page_number=1)

        links = getattr(request, REQUEST_JSONAPI_LINKS_ATTR)
        assert "first" in links
        assert "last" in links
        assert "page%5Bnumber%5D=1" in links["first"] or "page[number]=1" in links["first"]
        assert "page%5Bnumber%5D=5" in links["last"] or "page[number]=5" in links["last"]

    def test_no_prev_on_first_page(self):
        request = RequestFactory().get("/articles/")
        jsonapi_pagination(request, count=100, page_size=20, page_number=1)

        links = getattr(request, REQUEST_JSONAPI_LINKS_ATTR)
        assert "prev" not in links

    def test_prev_present_on_second_page(self):
        request = RequestFactory().get("/articles/")
        jsonapi_pagination(request, count=100, page_size=20, page_number=2)

        links = getattr(request, REQUEST_JSONAPI_LINKS_ATTR)
        assert "prev" in links

    def test_no_next_on_last_page(self):
        request = RequestFactory().get("/articles/")
        jsonapi_pagination(request, count=100, page_size=20, page_number=5)

        links = getattr(request, REQUEST_JSONAPI_LINKS_ATTR)
        assert "next" not in links

    def test_next_present_before_last_page(self):
        request = RequestFactory().get("/articles/")
        jsonapi_pagination(request, count=100, page_size=20, page_number=3)

        links = getattr(request, REQUEST_JSONAPI_LINKS_ATTR)
        assert "next" in links

    def test_preserves_existing_query_params(self):
        request = RequestFactory().get("/articles/?filter[status]=published&sort=-created")
        jsonapi_pagination(request, count=50, page_size=10, page_number=1)

        links = getattr(request, REQUEST_JSONAPI_LINKS_ATTR)
        # All links should preserve filter and sort
        for link_value in links.values():
            assert "filter" in link_value
            assert "sort" in link_value

    def test_page_size_in_links(self):
        request = RequestFactory().get("/articles/")
        jsonapi_pagination(request, count=50, page_size=25, page_number=1)

        links = getattr(request, REQUEST_JSONAPI_LINKS_ATTR)
        assert "25" in links["first"]

    def test_single_page(self):
        request = RequestFactory().get("/articles/")
        jsonapi_pagination(request, count=5, page_size=20, page_number=1)

        links = getattr(request, REQUEST_JSONAPI_LINKS_ATTR)
        assert "prev" not in links
        assert "next" not in links
        meta = getattr(request, REQUEST_JSONAPI_META_ATTR)
        assert meta["totalPages"] == 1


class TestJsonapiCursorPagination:
    def test_next_link_present_with_next_cursor(self):
        request = RequestFactory().get("/articles/")
        jsonapi_cursor_pagination(request, next_cursor="abc123")

        links = getattr(request, REQUEST_JSONAPI_LINKS_ATTR)
        assert "next" in links
        assert "abc123" in links["next"]

    def test_prev_link_present_with_prev_cursor(self):
        request = RequestFactory().get("/articles/")
        jsonapi_cursor_pagination(request, prev_cursor="xyz789")

        links = getattr(request, REQUEST_JSONAPI_LINKS_ATTR)
        assert "prev" in links
        assert "xyz789" in links["prev"]

    def test_no_links_when_no_cursors(self):
        request = RequestFactory().get("/articles/")
        jsonapi_cursor_pagination(request)

        links = getattr(request, REQUEST_JSONAPI_LINKS_ATTR, None)
        assert links is None or links == {}

    def test_both_cursors(self):
        request = RequestFactory().get("/articles/")
        jsonapi_cursor_pagination(request, next_cursor="next123", prev_cursor="prev456")

        links = getattr(request, REQUEST_JSONAPI_LINKS_ATTR)
        assert "next" in links
        assert "prev" in links

    def test_page_size_in_cursor_links(self):
        request = RequestFactory().get("/articles/")
        jsonapi_cursor_pagination(request, next_cursor="abc", page_size=50)

        links = getattr(request, REQUEST_JSONAPI_LINKS_ATTR)
        assert "50" in links["next"]


# ---------------------------------------------------------------------------
# jsonapi_paginate — high-level automatic pagination
# ---------------------------------------------------------------------------


class TestJsonapiPaginate:
    """Tests for the high-level jsonapi_paginate helper."""

    def test_returns_first_page_of_list(self):
        request = RequestFactory().get("/articles/")
        items = list(range(50))
        page = jsonapi_paginate(request, items, page_size=10)

        assert page == list(range(10))
        meta = getattr(request, REQUEST_JSONAPI_META_ATTR)
        assert meta["count"] == 50
        assert meta["totalPages"] == 5

    def test_returns_second_page(self):
        request = RequestFactory().get("/articles/?page[number]=2")
        items = list(range(50))
        page = jsonapi_paginate(request, items, page_size=10)

        assert page == list(range(10, 20))

    def test_reads_page_size_from_query_param(self):
        request = RequestFactory().get("/articles/?page[size]=5")
        items = list(range(50))
        page = jsonapi_paginate(request, items)

        assert len(page) == 5

    def test_sets_links(self):
        request = RequestFactory().get("/articles/")
        items = list(range(50))
        jsonapi_paginate(request, items, page_size=10)

        links = getattr(request, REQUEST_JSONAPI_LINKS_ATTR)
        assert "first" in links
        assert "last" in links
        assert "next" in links
        assert "prev" not in links  # first page

    def test_last_page_has_no_next(self):
        request = RequestFactory().get("/articles/?page[number]=5")
        items = list(range(50))
        jsonapi_paginate(request, items, page_size=10)

        links = getattr(request, REQUEST_JSONAPI_LINKS_ATTR)
        assert "next" not in links
        assert "prev" in links

    @override_settings(NINJA_JSONAPI={"MAX_PAGE_SIZE": 15})
    def test_clamps_to_max_page_size_from_settings(self):
        request = RequestFactory().get("/articles/?page[size]=100")
        items = list(range(50))
        page = jsonapi_paginate(request, items)

        assert len(page) == 15
        meta = getattr(request, REQUEST_JSONAPI_META_ATTR)
        assert meta["totalPages"] == 4  # ceil(50/15)

    def test_clamps_to_explicit_max_page_size(self):
        request = RequestFactory().get("/articles/?page[size]=100")
        items = list(range(50))
        page = jsonapi_paginate(request, items, max_page_size=25)

        assert len(page) == 25

    def test_works_with_queryset_like_objects(self):
        """Anything with __len__ and __getitem__ should work."""

        class FakeQuerySet:
            def __init__(self, data):
                self._data = data

            def __len__(self):
                return len(self._data)

            def __getitem__(self, key):
                return self._data[key]

        request = RequestFactory().get("/articles/")
        qs = FakeQuerySet(list(range(30)))
        page = jsonapi_paginate(request, qs, page_size=10)

        assert page == list(range(10))
        meta = getattr(request, REQUEST_JSONAPI_META_ATTR)
        assert meta["count"] == 30

    def test_empty_collection(self):
        request = RequestFactory().get("/articles/")
        page = jsonapi_paginate(request, [], page_size=10)

        assert page == []
        meta = getattr(request, REQUEST_JSONAPI_META_ATTR)
        assert meta["count"] == 0
        assert meta["totalPages"] == 1

    def test_page_number_below_one_defaults_to_one(self):
        request = RequestFactory().get("/articles/?page[number]=0")
        items = list(range(50))
        page = jsonapi_paginate(request, items, page_size=10)

        assert page == list(range(10))

    @override_settings(NINJA_JSONAPI={"DEFAULT_PAGE_SIZE": 7})
    def test_default_page_size_from_settings(self):
        request = RequestFactory().get("/articles/")
        items = list(range(50))
        page = jsonapi_paginate(request, items)

        assert len(page) == 7
