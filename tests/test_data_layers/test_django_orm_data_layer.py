from types import SimpleNamespace

import pytest
from django.test import RequestFactory

from django_ninja_jsonapi.data_layers.django_orm.orm import DjangoORMDataLayer


class _AttributesRecorder:
    def __init__(self):
        self.calls = []

    def model_dump(self, **kwargs):
        self.calls.append(kwargs)
        return {"name": None}


@pytest.mark.asyncio
async def test_create_object_uses_exclude_unset(monkeypatch):
    request = RequestFactory().post("/api/customers")
    data_layer = DjangoORMDataLayer(
        request=request,
        model=SimpleNamespace,
        schema=SimpleNamespace,
        resource_type="customer",
    )

    attributes = _AttributesRecorder()
    data_create = SimpleNamespace(attributes=attributes, id=None, relationships=None)

    async def fake_apply_relationships(*args, **kwargs):
        return None

    async def fake_start_nested_atomic():
        return None

    async def fake_end_nested_atomic(*args, **kwargs):
        return None

    monkeypatch.setattr(data_layer, "_apply_relationships", fake_apply_relationships)
    monkeypatch.setattr(data_layer, "_start_nested_atomic", fake_start_nested_atomic)
    monkeypatch.setattr(data_layer, "_end_nested_atomic", fake_end_nested_atomic)
    monkeypatch.setattr(
        "django_ninja_jsonapi.data_layers.django_orm.orm.BaseDjangoORM.create",
        lambda model, **kwargs: SimpleNamespace(id=1, **kwargs),
    )

    await data_layer.create_object(data_create=data_create, view_kwargs={})

    assert attributes.calls == [{"exclude_unset": True}]


@pytest.mark.asyncio
async def test_update_object_uses_exclude_unset(monkeypatch):
    request = RequestFactory().patch("/api/customers/1")
    data_layer = DjangoORMDataLayer(
        request=request,
        model=SimpleNamespace,
        schema=SimpleNamespace,
        resource_type="customer",
    )

    attributes = _AttributesRecorder()
    data_update = SimpleNamespace(attributes=attributes)

    async def fake_apply_relationships(*args, **kwargs):
        return None

    async def fake_start_nested_atomic():
        return None

    async def fake_end_nested_atomic(*args, **kwargs):
        return None

    monkeypatch.setattr(data_layer, "_apply_relationships", fake_apply_relationships)
    monkeypatch.setattr(data_layer, "_start_nested_atomic", fake_start_nested_atomic)
    monkeypatch.setattr(data_layer, "_end_nested_atomic", fake_end_nested_atomic)
    monkeypatch.setattr(
        "django_ninja_jsonapi.data_layers.django_orm.orm.BaseDjangoORM.update",
        lambda obj, **kwargs: obj,
    )

    await data_layer.update_object(obj=SimpleNamespace(id=1), data_update=data_update, view_kwargs={})

    assert attributes.calls == [{"exclude_unset": True}]


@pytest.mark.asyncio
async def test_delete_objects_uses_single_queryset_delete(monkeypatch):
    class FakeQuerySet:
        def __init__(self):
            self.filter_kwargs = None
            self.deleted = False

        def filter(self, **kwargs):
            self.filter_kwargs = kwargs
            return self

        def delete(self):
            self.deleted = True

    request = RequestFactory().delete("/api/customers")
    data_layer = DjangoORMDataLayer(
        request=request,
        model=SimpleNamespace,
        schema=SimpleNamespace,
        resource_type="customer",
    )
    queryset = FakeQuerySet()

    monkeypatch.setattr(
        "django_ninja_jsonapi.data_layers.django_orm.orm.models_storage.get_model_id_field_name",
        lambda resource_type: "id",
    )
    monkeypatch.setattr(
        "django_ninja_jsonapi.data_layers.django_orm.orm.BaseDjangoORM.queryset",
        lambda model: queryset,
    )

    await data_layer.delete_objects([SimpleNamespace(id=1), SimpleNamespace(id=2)], {})

    assert queryset.filter_kwargs == {"id__in": [1, 2]}
    assert queryset.deleted is True
