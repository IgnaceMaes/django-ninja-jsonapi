"""Tests for field_map parameter on jsonapi_filter."""

from django.test import RequestFactory

from django_ninja_jsonapi.response_helpers import jsonapi_filter


class FakeQuerySet:
    def __init__(self):
        self.calls = []

    def filter(self, *args, **kwargs):
        self.calls.append(("filter", args, kwargs))
        return self


class TestFieldMap:
    def test_field_map_remaps_filter_to_orm_field(self):
        request = RequestFactory().get("/articles/", {"filter[appointment_date]": "2024-01-01"})
        qs = FakeQuerySet()

        jsonapi_filter(
            request,
            qs,
            allowed_fields={"appointment_date"},
            field_map={"appointment_date": "appointment_dt__date"},
        )

        assert len(qs.calls) == 1
        # The Q object should use the mapped ORM field name
        q_obj = qs.calls[0][1][0]  # first positional arg is the Q object
        # Q objects store children as (field, value) tuples
        assert ("appointment_dt__date", "2024-01-01") in q_obj.children

    def test_field_map_unmapped_fields_use_default_conversion(self):
        request = RequestFactory().get("/articles/", {"filter[status]": "active"})
        qs = FakeQuerySet()

        jsonapi_filter(
            request,
            qs,
            allowed_fields={"status"},
            field_map={"appointment_date": "appointment_dt__date"},
        )

        assert len(qs.calls) == 1
        q_obj = qs.calls[0][1][0]
        assert ("status", "active") in q_obj.children

    def test_field_map_with_dot_path_in_filter_name(self):
        request = RequestFactory().get("/articles/", {"filter[author.name]": "Alice"})
        qs = FakeQuerySet()

        jsonapi_filter(
            request,
            qs,
            allowed_fields={"author.name"},
            field_map={"author.name": "author__user__first_name"},
        )

        assert len(qs.calls) == 1
        q_obj = qs.calls[0][1][0]
        assert ("author__user__first_name", "Alice") in q_obj.children

    def test_field_map_none_behaves_as_default(self):
        request = RequestFactory().get("/articles/", {"filter[status]": "active"})
        qs = FakeQuerySet()

        jsonapi_filter(request, qs, allowed_fields={"status"}, field_map=None)

        assert len(qs.calls) == 1

    def test_field_map_combined_with_allowed_fields(self):
        request = RequestFactory().get(
            "/articles/",
            {"filter[appointment_date]": "2024-01-01", "filter[secret]": "oops"},
        )
        qs = FakeQuerySet()

        jsonapi_filter(
            request,
            qs,
            allowed_fields={"appointment_date"},
            field_map={"appointment_date": "appointment_dt__date"},
        )

        assert len(qs.calls) == 1
        q_obj = qs.calls[0][1][0]
        # Only the allowed + mapped field should be present
        assert ("appointment_dt__date", "2024-01-01") in q_obj.children
        field_names = [child[0] for child in q_obj.children]
        assert "secret" not in field_names
