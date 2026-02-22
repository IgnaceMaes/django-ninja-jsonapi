from types import SimpleNamespace

import pytest
from django.test import RequestFactory

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
