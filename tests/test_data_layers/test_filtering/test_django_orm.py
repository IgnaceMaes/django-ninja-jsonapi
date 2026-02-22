from django_ninja_jsonapi.data_layers.django_orm.query_building import apply_filters, apply_sorts


class FakeQuerySet:
    def __init__(self):
        self.calls = []

    def filter(self, **kwargs):
        self.calls.append(("filter", kwargs))
        return self

    def exclude(self, **kwargs):
        self.calls.append(("exclude", kwargs))
        return self

    def order_by(self, *args):
        self.calls.append(("order_by", args))
        return self


def test_apply_filters_maps_common_jsonapi_operators_to_django_lookups():
    queryset = FakeQuerySet()

    apply_filters(
        queryset,
        [
            {"name": "name", "op": "eq", "val": "john"},
            {"name": "age", "op": "ne", "val": 18},
            {"name": "score", "op": "lt", "val": 90},
            {"name": "score", "op": "ge", "val": 60},
            {"name": "author.name", "op": "ilike", "val": "jo"},
            {"name": "tags", "op": "in", "val": ["a", "b"]},
            {"name": "status", "op": "not_in", "val": ["archived"]},
            {"name": "deleted_at", "op": "is_null", "val": True},
        ],
    )

    assert queryset.calls == [
        ("filter", {"name": "john"}),
        ("exclude", {"age": 18}),
        ("filter", {"score__lt": 90}),
        ("filter", {"score__gte": 60}),
        ("filter", {"author__name__icontains": "jo"}),
        ("filter", {"tags__in": ["a", "b"]}),
        ("exclude", {"status__in": ["archived"]}),
        ("filter", {"deleted_at__isnull": True}),
    ]


def test_apply_sorts_maps_relationship_paths_and_desc_order():
    queryset = FakeQuerySet()

    apply_sorts(
        queryset,
        [
            {"field": "author.name", "order": "desc"},
            {"field": "created_at", "order": "asc"},
        ],
    )

    assert queryset.calls == [("order_by", ("-author__name", "created_at"))]
