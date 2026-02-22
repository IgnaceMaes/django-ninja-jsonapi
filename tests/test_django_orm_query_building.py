from django.db.models import Q

from django_ninja_jsonapi.data_layers.django_orm.query_building import apply_filters, apply_sorts


class FakeQuerySet:
    def __init__(self):
        self.calls = []

    def filter(self, *args, **kwargs):
        self.calls.append(("filter", args, kwargs))
        return self

    def exclude(self, **kwargs):
        self.calls.append(("exclude", (), kwargs))
        return self

    def order_by(self, *args):
        self.calls.append(("order_by", args))
        return self


def test_apply_filters_maps_jsonapi_ops_to_django_lookups():
    queryset = FakeQuerySet()

    apply_filters(
        queryset,
        [
            {"name": "name", "op": "eq", "val": "john"},
            {"name": "age", "op": "ne", "val": 18},
            {"name": "score", "op": "lt", "val": 90},
            {"name": "author.name", "op": "ilike", "val": "jo"},
            {"name": "tags", "op": "in", "val": ["a", "b"]},
            {"name": "deleted_at", "op": "is_null", "val": True},
        ],
    )

    assert len(queryset.calls) == 6
    for call in queryset.calls:
        assert call[0] == "filter"
        assert len(call[1]) == 1
        assert isinstance(call[1][0], Q)


def test_apply_filters_supports_logical_or_grouping():
    queryset = FakeQuerySet()

    apply_filters(
        queryset,
        [
            {
                "or": [
                    {"name": "status", "op": "eq", "val": "active"},
                    {"name": "status", "op": "eq", "val": "pending"},
                ]
            }
        ],
    )

    assert len(queryset.calls) == 1
    assert queryset.calls[0][0] == "filter"
    assert len(queryset.calls[0][1]) == 1
    assert isinstance(queryset.calls[0][1][0], Q)


def test_apply_sorts_maps_relationship_paths_and_desc_order():
    queryset = FakeQuerySet()

    apply_sorts(
        queryset,
        [
            {"field": "author.name", "order": "desc"},
            {"field": "created_at", "order": "asc"},
        ],
    )

    assert queryset.calls == [
        ("order_by", ("-author__name", "created_at")),
    ]
