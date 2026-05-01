"""Tests for standalone helpers: jsonapi_sort, jsonapi_filter, parse_include."""

from django.test import RequestFactory

from django_ninja_jsonapi.response_helpers import jsonapi_filter, jsonapi_sort, parse_include


# ---------------------------------------------------------------------------
# FakeQuerySet — lightweight stand-in for Django QuerySet
# ---------------------------------------------------------------------------


class FakeQuerySet:
    def __init__(self, data=None):
        self.data = data or []
        self.calls = []

    def order_by(self, *args):
        self.calls.append(("order_by", args))
        return self

    def filter(self, *args, **kwargs):
        self.calls.append(("filter", args, kwargs))
        return self


# ===========================================================================
# jsonapi_sort tests
# ===========================================================================


class TestJsonapiSort:
    def test_no_sort_param_returns_queryset_unchanged(self):
        request = RequestFactory().get("/articles/")
        qs = FakeQuerySet()

        result = jsonapi_sort(request, qs)

        assert result is qs
        assert len(qs.calls) == 0

    def test_single_ascending_field(self):
        request = RequestFactory().get("/articles/?sort=name")
        qs = FakeQuerySet()

        jsonapi_sort(request, qs)

        assert qs.calls == [("order_by", ("name",))]

    def test_single_descending_field(self):
        request = RequestFactory().get("/articles/?sort=-created_dt")
        qs = FakeQuerySet()

        jsonapi_sort(request, qs)

        assert qs.calls == [("order_by", ("-created_dt",))]

    def test_multiple_fields(self):
        request = RequestFactory().get("/articles/?sort=-created_dt,name")
        qs = FakeQuerySet()

        jsonapi_sort(request, qs)

        assert qs.calls == [("order_by", ("-created_dt", "name"))]

    def test_relationship_path_converts_to_orm_lookup(self):
        request = RequestFactory().get("/articles/?sort=author.name")
        qs = FakeQuerySet()

        jsonapi_sort(request, qs)

        assert qs.calls == [("order_by", ("author__name",))]

    def test_allowed_fields_filters_out_disallowed(self):
        request = RequestFactory().get("/articles/?sort=-created_dt,name,disallowed")
        qs = FakeQuerySet()

        jsonapi_sort(request, qs, allowed_fields={"created_dt", "name"})

        assert qs.calls == [("order_by", ("-created_dt", "name"))]

    def test_allowed_fields_all_filtered_returns_unchanged(self):
        request = RequestFactory().get("/articles/?sort=disallowed")
        qs = FakeQuerySet()

        result = jsonapi_sort(request, qs, allowed_fields={"name"})

        assert result is qs
        assert len(qs.calls) == 0

    def test_empty_sort_param_returns_unchanged(self):
        request = RequestFactory().get("/articles/?sort=")
        qs = FakeQuerySet()

        result = jsonapi_sort(request, qs)

        assert result is qs

    def test_no_allowed_fields_means_all_allowed(self):
        request = RequestFactory().get("/articles/?sort=anything,-whatever")
        qs = FakeQuerySet()

        jsonapi_sort(request, qs)

        assert qs.calls == [("order_by", ("anything", "-whatever"))]


# ===========================================================================
# parse_include tests
# ===========================================================================


class TestParseInclude:
    def test_no_include_param_returns_empty_set(self):
        request = RequestFactory().get("/articles/1/")

        result = parse_include(request)

        assert result == set()

    def test_single_include(self):
        request = RequestFactory().get("/articles/1/?include=author")

        result = parse_include(request)

        assert result == {"author"}

    def test_multiple_includes(self):
        request = RequestFactory().get("/articles/1/?include=author,comments")

        result = parse_include(request)

        assert result == {"author", "comments"}

    def test_nested_include_paths(self):
        request = RequestFactory().get("/articles/1/?include=memberships,memberships.user")

        result = parse_include(request)

        assert result == {"memberships", "memberships.user"}

    def test_empty_include_param_returns_empty_set(self):
        request = RequestFactory().get("/articles/1/?include=")

        result = parse_include(request)

        assert result == set()

    def test_whitespace_around_paths_is_stripped(self):
        request = RequestFactory().get("/articles/1/?include= author , comments ")

        result = parse_include(request)

        assert result == {"author", "comments"}


# ===========================================================================
# jsonapi_filter tests
# ===========================================================================


class TestJsonapiFilter:
    def test_no_filter_params_returns_queryset_unchanged(self):
        request = RequestFactory().get("/articles/")
        qs = FakeQuerySet()

        result = jsonapi_filter(request, qs)

        assert result is qs
        assert len(qs.calls) == 0

    def test_single_filter(self):
        request = RequestFactory().get("/articles/", {"filter[status]": "published"})
        qs = FakeQuerySet()

        jsonapi_filter(request, qs)

        assert len(qs.calls) == 1
        assert qs.calls[0][0] == "filter"

    def test_multiple_filters(self):
        request = RequestFactory().get(
            "/articles/",
            {"filter[status]": "published", "filter[author]": "5"},
        )
        qs = FakeQuerySet()

        jsonapi_filter(request, qs)

        assert len(qs.calls) == 1  # combined into single Q

    def test_relationship_path_converts_to_orm_lookup(self):
        request = RequestFactory().get("/articles/", {"filter[author.name]": "Alice"})
        qs = FakeQuerySet()

        jsonapi_filter(request, qs)

        assert len(qs.calls) == 1

    def test_allowed_fields_filters_out_disallowed(self):
        request = RequestFactory().get(
            "/articles/",
            {"filter[status]": "published", "filter[secret]": "oops"},
        )
        qs = FakeQuerySet()

        jsonapi_filter(request, qs, allowed_fields={"status"})

        assert len(qs.calls) == 1

    def test_allowed_fields_all_filtered_returns_unchanged(self):
        request = RequestFactory().get("/articles/", {"filter[secret]": "oops"})
        qs = FakeQuerySet()

        result = jsonapi_filter(request, qs, allowed_fields={"status"})

        assert result is qs
        assert len(qs.calls) == 0

    def test_non_filter_params_are_ignored(self):
        request = RequestFactory().get("/articles/?sort=name&page[number]=1")
        qs = FakeQuerySet()

        result = jsonapi_filter(request, qs)

        assert result is qs
        assert len(qs.calls) == 0

    def test_no_allowed_fields_means_all_allowed(self):
        request = RequestFactory().get("/articles/", {"filter[anything]": "val"})
        qs = FakeQuerySet()

        jsonapi_filter(request, qs)

        assert len(qs.calls) == 1
