from types import SimpleNamespace

import pytest
from django.test import RequestFactory, override_settings

from django_ninja_jsonapi.data_layers.django_orm.orm import DjangoORMDataLayer
from django_ninja_jsonapi.exceptions import InvalidInclude
from django_ninja_jsonapi.types_metadata import RelationshipInfo
from django_ninja_jsonapi.views.enums import Operation
from django_ninja_jsonapi.views.view_base import ViewBase


class DummyView(ViewBase):
    pass


def test_process_includes_raises_invalid_include_for_unknown_relationship(monkeypatch):
    request = RequestFactory().get("/api/customers", {"include": "computers"})
    view = DummyView(
        request=request,
        resource_type="customer",
        operation=Operation.GET_LIST,
        model=SimpleNamespace,
        schema=SimpleNamespace,
    )

    monkeypatch.setattr(
        "django_ninja_jsonapi.views.view_base.schemas_storage.get_relationship_info",
        lambda resource_type, operation_type, field_name: None,
    )
    monkeypatch.setattr(
        "django_ninja_jsonapi.views.view_base.models_storage.get_resource_path",
        lambda resource_type: f"/{resource_type}s",
    )
    monkeypatch.setattr(
        "django_ninja_jsonapi.views.view_base.models_storage.get_object_id",
        lambda db_item, resource_type: getattr(db_item, "id", "1"),
    )

    with pytest.raises(InvalidInclude) as exc_info:
        view._process_includes(
            db_items=[SimpleNamespace()],
            items_data=[{}],
            resource_type="customer",
            include_paths=[["computers"]],
            include_fields={},
        )

    assert "Relationship 'computers' is not available" in exc_info.value.as_dict["detail"]


def test_process_includes_handles_django_related_manager(monkeypatch):
    class FakeRelatedManager:
        def __init__(self, items):
            self._items = items

        def all(self):
            return self._items

    request = RequestFactory().get("/api/customers", {"include": "computers"})
    view = DummyView(
        request=request,
        resource_type="customer",
        operation=Operation.GET_LIST,
        model=SimpleNamespace,
        schema=SimpleNamespace,
    )

    monkeypatch.setattr(
        "django_ninja_jsonapi.views.view_base.schemas_storage.get_relationship_info",
        lambda resource_type, operation_type, field_name: RelationshipInfo(resource_type="computer", many=True),
    )
    monkeypatch.setattr(
        "django_ninja_jsonapi.views.view_base.models_storage.get_resource_path",
        lambda resource_type: f"/{resource_type}s",
    )
    monkeypatch.setattr(
        "django_ninja_jsonapi.views.view_base.models_storage.get_object_id",
        lambda db_item, resource_type: getattr(db_item, "id", "1"),
    )
    monkeypatch.setattr(
        view,
        "_prepare_item_data",
        lambda db_item, resource_type, include_fields=None: {
            "id": str(db_item.id),
            "type": resource_type,
            "attributes": {},
        },
    )

    related = SimpleNamespace(id=1)
    db_item = SimpleNamespace(computers=FakeRelatedManager([related]))
    item_data = {}

    included = view._process_includes(
        db_items=[db_item],
        items_data=[item_data],
        resource_type="customer",
        include_paths=[["computers"]],
        include_fields={},
    )

    assert item_data["relationships"]["computers"]["data"] == [{"id": "1", "type": "computer"}]
    assert "links" in item_data["relationships"]["computers"]
    assert set(item_data["relationships"]["computers"]["links"]) == {"self", "related"}
    assert included[("computer", "1")]["type"] == "computer"


def test_process_includes_uses_mapped_model_field_name(monkeypatch):
    request = RequestFactory().get("/api/computers", {"include": "customers"})
    view = DummyView(
        request=request,
        resource_type="computer",
        operation=Operation.GET_LIST,
        model=SimpleNamespace,
        schema=SimpleNamespace,
    )

    monkeypatch.setattr(
        "django_ninja_jsonapi.views.view_base.schemas_storage.get_relationship_info",
        lambda resource_type, operation_type, field_name: RelationshipInfo(
            resource_type="customer",
            model_field_name="owner",
        ),
    )
    monkeypatch.setattr(
        "django_ninja_jsonapi.views.view_base.models_storage.get_resource_path",
        lambda resource_type: f"/{resource_type}s",
    )
    monkeypatch.setattr(
        "django_ninja_jsonapi.views.view_base.models_storage.get_object_id",
        lambda db_item, resource_type: getattr(db_item, "id", "1"),
    )
    monkeypatch.setattr(
        view,
        "_prepare_item_data",
        lambda db_item, resource_type, include_fields=None: {
            "id": str(db_item.id),
            "type": resource_type,
            "attributes": {},
        },
    )

    owner = SimpleNamespace(id=7)
    db_item = SimpleNamespace(owner=owner)
    item_data = {}

    included = view._process_includes(
        db_items=[db_item],
        items_data=[item_data],
        resource_type="computer",
        include_paths=[["customers"]],
        include_fields={},
    )

    assert item_data["relationships"]["customers"]["data"] == {"id": "7", "type": "customer"}
    assert set(item_data["relationships"]["customers"]["links"]) == {"self", "related"}
    assert included[("customer", "7")]["type"] == "customer"


def test_map_include_path_to_prefetch_uses_mapped_model_field_name(monkeypatch):
    request = RequestFactory().get("/api/computers", {"include": "customers"})
    data_layer = DjangoORMDataLayer(
        request=request,
        model=SimpleNamespace,
        schema=SimpleNamespace,
        resource_type="computer",
    )

    monkeypatch.setattr(
        "django_ninja_jsonapi.data_layers.django_orm.orm.schemas_storage.get_relationship_info",
        lambda resource_type, operation_type, field_name: RelationshipInfo(
            resource_type="customer",
            model_field_name="owner",
        ),
    )

    assert data_layer._map_include_path_to_prefetch("customers") == "owner"


def test_apply_querystring_splits_select_and_prefetch(monkeypatch):
    class FakeQuerySet:
        def __init__(self):
            self.selected = []
            self.prefetched = []

        def filter(self, **kwargs):
            return self

        def order_by(self, *args):
            return self

        def select_related(self, *args):
            self.selected.extend(args)
            return self

        def prefetch_related(self, *args):
            self.prefetched.extend(args)
            return self

        def only(self, *args):
            return self

    request = RequestFactory().get("/api/computers", {"include": "owner,groups"})
    data_layer = DjangoORMDataLayer(
        request=request,
        model=SimpleNamespace,
        schema=SimpleNamespace,
        resource_type="computer",
    )

    fake_qs = FakeQuerySet()
    qs_manager = DummyView(
        request=request,
        resource_type="computer",
        operation=Operation.GET_LIST,
        model=SimpleNamespace,
        schema=SimpleNamespace,
    ).query_params

    monkeypatch.setattr(data_layer, "_map_include_path_to_prefetch", lambda include_path: include_path)
    monkeypatch.setattr(
        data_layer,
        "_is_select_related_include_path",
        lambda include_path: include_path == "owner",
    )

    data_layer._apply_querystring(fake_qs, qs_manager)

    assert fake_qs.selected == ["owner"]
    assert fake_qs.prefetched == ["groups"]


def test_apply_querystring_uses_include_mappings(monkeypatch):
    class FakeQuerySet:
        def __init__(self):
            self.selected = []
            self.prefetched = []

        def filter(self, **kwargs):
            return self

        def order_by(self, *args):
            return self

        def select_related(self, *args):
            self.selected.extend(args)
            return self

        def prefetch_related(self, *args):
            self.prefetched.extend(args)
            return self

        def only(self, *args):
            return self

    request = RequestFactory().get("/api/computers", {"include": "owner"})
    data_layer = DjangoORMDataLayer(
        request=request,
        model=SimpleNamespace,
        schema=SimpleNamespace,
        resource_type="computer",
        select_for_includes={"__all__": ["company"], "owner": ["owner__profile"]},
        prefetch_for_includes={"owner": ["owner__groups"]},
    )

    fake_qs = FakeQuerySet()
    qs_manager = DummyView(
        request=request,
        resource_type="computer",
        operation=Operation.GET_LIST,
        model=SimpleNamespace,
        schema=SimpleNamespace,
    ).query_params

    monkeypatch.setattr(data_layer, "_map_include_path_to_prefetch", lambda include_path: include_path)
    monkeypatch.setattr(data_layer, "_is_select_related_include_path", lambda include_path: True)

    data_layer._apply_querystring(fake_qs, qs_manager)

    assert sorted(fake_qs.selected) == ["company", "owner", "owner__profile"]
    assert fake_qs.prefetched == ["owner__groups"]


def test_build_list_response_includes_top_level_links(monkeypatch):
    request = RequestFactory().get("/api/customers", {"page[number]": "2", "page[size]": "2"})
    view = DummyView(
        request=request,
        resource_type="customer",
        operation=Operation.GET_LIST,
        model=SimpleNamespace,
        schema=SimpleNamespace,
    )

    monkeypatch.setattr(
        "django_ninja_jsonapi.views.view_base.models_storage.get_resource_path",
        lambda resource_type: "/customers" if resource_type == "customer" else f"/{resource_type}s",
    )
    monkeypatch.setattr(
        "django_ninja_jsonapi.views.view_base.models_storage.get_object_id",
        lambda db_item, resource_type: db_item.id,
    )
    monkeypatch.setattr(
        view,
        "_prepare_item_data",
        lambda db_item, resource_type, include_fields=None: {
            "id": str(db_item.id),
            "type": resource_type,
            "attributes": {},
            "links": {},
        },
    )

    response = view._build_list_response(
        items_from_db=[SimpleNamespace(id=1), SimpleNamespace(id=2)],
        count=6,
        total_pages=3,
    )

    assert "links" in response
    assert set(response["links"]) == {"self", "first", "last", "prev", "next"}
    assert response["data"][0]["links"]["self"].endswith("/api/customers/1/")


def test_build_detail_response_includes_top_level_self_link(monkeypatch):
    request = RequestFactory().get("/api/customers/1")
    view = DummyView(
        request=request,
        resource_type="customer",
        operation=Operation.GET,
        model=SimpleNamespace,
        schema=SimpleNamespace,
    )

    monkeypatch.setattr(
        "django_ninja_jsonapi.views.view_base.models_storage.get_resource_path",
        lambda resource_type: "/customers" if resource_type == "customer" else f"/{resource_type}s",
    )
    monkeypatch.setattr(
        "django_ninja_jsonapi.views.view_base.models_storage.get_object_id",
        lambda db_item, resource_type: db_item.id,
    )
    monkeypatch.setattr(
        view,
        "_prepare_item_data",
        lambda db_item, resource_type, include_fields=None: {
            "id": str(db_item.id),
            "type": resource_type,
            "attributes": {},
            "links": {},
        },
    )

    response = view._build_detail_response(SimpleNamespace(id=1))

    assert response["links"]["self"].endswith("/api/customers/1")
    assert response["data"]["links"]["self"].endswith("/api/customers/1/")


def test_build_list_response_with_cursor_has_next_link(monkeypatch):
    request = RequestFactory().get("/api/customers", {"page[cursor]": "10", "page[size]": "2"})
    view = DummyView(
        request=request,
        resource_type="customer",
        operation=Operation.GET_LIST,
        model=SimpleNamespace,
        schema=SimpleNamespace,
    )
    view.query_params.pagination.next_cursor = "12"

    monkeypatch.setattr(
        "django_ninja_jsonapi.views.view_base.models_storage.get_resource_path",
        lambda resource_type: "/customers",
    )
    monkeypatch.setattr(
        "django_ninja_jsonapi.views.view_base.models_storage.get_object_id",
        lambda db_item, resource_type: db_item.id,
    )
    monkeypatch.setattr(
        view,
        "_prepare_item_data",
        lambda db_item, resource_type, include_fields=None: {
            "id": str(db_item.id),
            "type": resource_type,
            "attributes": {},
            "links": {},
        },
    )

    response = view._build_list_response([SimpleNamespace(id=11), SimpleNamespace(id=12)], count=None, total_pages=None)

    assert response["links"]["next"] is not None
    assert "page%5Bcursor%5D=12" in response["links"]["next"]


def test_detail_response_omits_jsonapi_by_default(monkeypatch):
    request = RequestFactory().get("/api/customers/1")
    view = DummyView(
        request=request,
        resource_type="customer",
        operation=Operation.GET,
        model=SimpleNamespace,
        schema=SimpleNamespace,
    )

    monkeypatch.setattr(
        "django_ninja_jsonapi.views.view_base.models_storage.get_resource_path",
        lambda resource_type: "/customers",
    )
    monkeypatch.setattr(
        "django_ninja_jsonapi.views.view_base.models_storage.get_object_id",
        lambda db_item, resource_type: db_item.id,
    )
    monkeypatch.setattr(
        view,
        "_prepare_item_data",
        lambda db_item, resource_type, include_fields=None: {
            "id": str(db_item.id),
            "type": resource_type,
            "attributes": {},
            "links": {},
        },
    )

    response = view._build_detail_response(SimpleNamespace(id=1))

    assert "jsonapi" not in response


@override_settings(NINJA_JSONAPI={"INCLUDE_JSONAPI_OBJECT": True, "JSONAPI_VERSION": "1.0"})
def test_detail_response_includes_jsonapi_when_enabled(monkeypatch):
    request = RequestFactory().get("/api/customers/1")
    view = DummyView(
        request=request,
        resource_type="customer",
        operation=Operation.GET,
        model=SimpleNamespace,
        schema=SimpleNamespace,
    )

    monkeypatch.setattr(
        "django_ninja_jsonapi.views.view_base.models_storage.get_resource_path",
        lambda resource_type: "/customers",
    )
    monkeypatch.setattr(
        "django_ninja_jsonapi.views.view_base.models_storage.get_object_id",
        lambda db_item, resource_type: db_item.id,
    )
    monkeypatch.setattr(
        view,
        "_prepare_item_data",
        lambda db_item, resource_type, include_fields=None: {
            "id": str(db_item.id),
            "type": resource_type,
            "attributes": {},
            "links": {},
        },
    )

    response = view._build_detail_response(SimpleNamespace(id=1))

    assert response["jsonapi"] == {"version": "1.0"}


def test_prepare_item_data_extracts_resource_meta_fields(monkeypatch):
    class FakeAttrsSchema:
        @staticmethod
        def model_validate(db_item):
            return {
                "name": db_item.name,
                "status": db_item.status,
            }

    class FakeDataSchema:
        def __init__(self, id, attributes):
            self.id = id
            self.attributes = attributes

        def model_dump(self):
            return {
                "id": self.id,
                "type": "customer",
                "attributes": dict(self.attributes),
            }

    monkeypatch.setattr(
        "django_ninja_jsonapi.views.view_base.models_storage.get_object_id",
        lambda db_item, resource_type: db_item.id,
    )
    monkeypatch.setattr(
        "django_ninja_jsonapi.views.view_base.schemas_storage.get_attrs_schema",
        lambda resource_type, operation_type: FakeAttrsSchema,
    )
    monkeypatch.setattr(
        "django_ninja_jsonapi.views.view_base.schemas_storage.get_data_schema",
        lambda resource_type, operation_type: FakeDataSchema,
    )
    monkeypatch.setattr(
        "django_ninja_jsonapi.views.view_base.schemas_storage.get_meta_fields",
        lambda resource_type, operation_type: ["status"],
    )

    item_data = DummyView._prepare_item_data(
        db_item=SimpleNamespace(id=1, name="John", status="active"),
        resource_type="customer",
        include_fields=None,
    )

    assert item_data["attributes"] == {"name": "John"}
    assert item_data["meta"] == {"status": "active"}


def test_prepare_item_data_omits_resource_meta_when_not_configured(monkeypatch):
    class FakeFieldSchema:
        def __init__(self, name):
            self.name = name

    monkeypatch.setattr(
        "django_ninja_jsonapi.views.view_base.models_storage.get_object_id",
        lambda db_item, resource_type: db_item.id,
    )
    monkeypatch.setattr(
        "django_ninja_jsonapi.views.view_base.schemas_storage.get_meta_fields",
        lambda resource_type, operation_type: [],
    )
    monkeypatch.setattr(
        "django_ninja_jsonapi.views.view_base.schemas_storage.get_attrs_schema",
        lambda resource_type, operation_type: object,
    )
    monkeypatch.setattr(
        "django_ninja_jsonapi.views.view_base.schemas_storage.get_model_validators",
        lambda resource_type, operation_type: ({}, {}),
    )

    item_data = DummyView._prepare_item_data(
        db_item=SimpleNamespace(id=1, name="John"),
        resource_type="customer",
        include_fields={"customer": {"name": FakeFieldSchema}},
    )

    assert item_data["attributes"] == {"name": "John"}
    assert "meta" not in item_data
