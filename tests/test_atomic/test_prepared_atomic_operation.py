from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from django_ninja_jsonapi.atomic.prepared_atomic_operation import OperationBase, OperationRemove, OperationUpdate
from django_ninja_jsonapi.atomic.schemas import AtomicOperationRef, OperationItemInSchema, OperationRelationshipSchema
from django_ninja_jsonapi.types_metadata import RelationshipInfo
from django_ninja_jsonapi.views import Operation, OperationConfig


class DummyDL:
    url_id_field = "id"

    def __init__(self):
        self.called = None

    async def update_relationship(self, json_data, relationship_field, related_id_field, view_kwargs):
        self.called = {
            "json_data": json_data,
            "relationship_field": relationship_field,
            "related_id_field": related_id_field,
            "view_kwargs": view_kwargs,
        }


class DummyView:
    def __init__(self):
        self.updated = None

    async def process_update_object(self, dl, obj_id, data_update):
        self.updated = {
            "obj_id": obj_id,
            "data_update": data_update,
        }
        return {"data": {"id": obj_id}}

    async def handle_get_resource_detail(self, obj_id):
        return {"data": {"id": obj_id}}

    async def process_delete_object(self, dl, obj_id):
        return None


class DummySchemaIn:
    def __call__(self, *, data):
        payload = SimpleNamespace(
            id=data["id"],
            attributes=SimpleNamespace(model_fields={"name": None}),
        )
        return SimpleNamespace(data=payload)


@pytest.mark.asyncio
async def test_operation_update_uses_update_schema_and_processes_object_update(monkeypatch):
    op = OperationUpdate(
        view=DummyView(),
        ref=AtomicOperationRef(type="user", id="1"),
        data=OperationItemInSchema(type="user", attributes={"name": "John"}),
        op_type="update",
        resource_type="user",
    )

    called = {}

    def fake_get_schema_in(resource_type, operation_type):
        called["resource_type"] = resource_type
        called["operation_type"] = operation_type
        return DummySchemaIn()

    monkeypatch.setattr(
        "django_ninja_jsonapi.atomic.prepared_atomic_operation.schemas_storage.get_schema_in",
        fake_get_schema_in,
    )

    result = await op.handle(DummyDL())

    assert called == {"resource_type": "user", "operation_type": "update"}
    assert result == {"data": {"id": "1"}}
    assert op.view.updated["obj_id"] == "1"


@pytest.mark.asyncio
async def test_operation_update_relationship_uses_data_layer_relationship_update(monkeypatch):
    dl = DummyDL()
    op = OperationUpdate(
        view=DummyView(),
        ref=AtomicOperationRef(type="user", id="1", relationship="computers"),
        data=[OperationRelationshipSchema(type="computer", id="10")],
        op_type="update",
        resource_type="user",
    )

    monkeypatch.setattr(
        "django_ninja_jsonapi.atomic.prepared_atomic_operation.schemas_storage.get_relationship_info",
        lambda resource_type, operation_type, field_name: RelationshipInfo(resource_type="computer", many=True),
    )

    result = await op.handle(dl)

    assert result == {"data": {"id": "1"}}
    assert dl.called == {
        "json_data": {"data": [{"id": "10", "type": "computer"}]},
        "relationship_field": "computers",
        "related_id_field": "id",
        "view_kwargs": {"id": "1"},
    }


def test_operation_update_resolves_ref_lid_and_relationship_lids():
    op = OperationUpdate(
        view=DummyView(),
        ref=AtomicOperationRef(type="user", lid="u-lid", relationship="computers"),
        data=OperationItemInSchema(
            type="user",
            attributes={},
            relationships={
                "computers": {
                    "data": [
                        {"type": "computer", "lid": "c-lid"},
                    ]
                }
            },
        ),
        op_type="update",
        resource_type="user",
    )

    op.update_relationships_with_lid(
        {
            "user": {"u-lid": "1"},
            "computer": {"c-lid": "10"},
        }
    )

    assert op.ref.id == "1"
    assert op.ref.lid is None
    assert op.data.relationships["computers"]["data"][0]["id"] == "10"
    assert "lid" not in op.data.relationships["computers"]["data"][0]


@pytest.mark.asyncio
async def test_operation_update_relationship_rejects_non_relationship_payload(monkeypatch):
    op = OperationUpdate(
        view=DummyView(),
        ref=AtomicOperationRef(type="user", id="1", relationship="computers"),
        data=OperationItemInSchema(type="user", attributes={"name": "John"}),
        op_type="update",
        resource_type="user",
    )

    monkeypatch.setattr(
        "django_ninja_jsonapi.atomic.prepared_atomic_operation.schemas_storage.get_relationship_info",
        lambda resource_type, operation_type, field_name: RelationshipInfo(resource_type="computer", many=True),
    )

    with pytest.raises(ValueError, match="Atomic relationship update expects relationship linkage data"):
        await op.handle(DummyDL())


@pytest.mark.asyncio
async def test_operation_remove_requires_ref_id():
    op = OperationRemove(
        view=DummyView(),
        ref=AtomicOperationRef(type="user", lid="u-lid"),
        data=None,
        op_type="remove",
        resource_type="user",
    )

    with pytest.raises(ValueError, match="must contain an 'id'"):
        await op.handle(DummyDL())


@pytest.mark.asyncio
async def test_handle_view_dependencies_merges_all_and_specific_defaults():
    class CommonDeps(BaseModel):
        page_size: int = 10
        source: str = "common"

    class UpdateDeps(BaseModel):
        source: str = "update"
        include_archived: bool = False

    class DummyViewWithDeps:
        operation_dependencies = {
            Operation.ALL: OperationConfig(dependencies=CommonDeps),
            Operation.UPDATE: OperationConfig(dependencies=UpdateDeps),
        }

    merged = await OperationBase.handle_view_dependencies(
        request=SimpleNamespace(),
        view_cls=DummyViewWithDeps,
        resource_type="user",
        operation=Operation.UPDATE,
    )

    assert merged == {
        "page_size": 10,
        "source": "update",
        "include_archived": False,
    }
