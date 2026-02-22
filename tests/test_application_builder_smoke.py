import pytest
from ninja import NinjaAPI
from pydantic import BaseModel

from django_ninja_jsonapi.api.application_builder import ApplicationBuilder, ApplicationBuilderError
from django_ninja_jsonapi.views.enums import Operation


class DummyModel:
    id = 1


class DummySchema(BaseModel):
    name: str


class DummyView:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    async def handle_get_resource_detail(self, obj_id: str):
        return {"data": {"type": "dummy", "id": obj_id, "attributes": {"name": "x"}}}

    async def handle_get_resource_list(self):
        return {"data": []}

    async def handle_post_resource_list(self, data_create):
        return {"data": {"type": "dummy", "id": "1", "attributes": data_create.attributes.model_dump()}}

    async def handle_update_resource(self, obj_id: str, data_update):
        return {"data": {"type": "dummy", "id": obj_id, "attributes": data_update.attributes.model_dump()}}

    async def handle_delete_resource(self, obj_id: str):
        return None

    async def handle_delete_resource_list(self):
        return {"data": []}


def test_builder_initializes_and_registers_routes():
    api = NinjaAPI()
    builder = ApplicationBuilder(api)

    builder.add_resource(
        path="/dummy",
        tags=["dummy"],
        resource_type="dummy",
        view=DummyView,
        model=DummyModel,
        schema=DummySchema,
        operations=[Operation.GET_LIST, Operation.GET],
    )

    initialized = builder.initialize()
    assert initialized is api

    route_keys = []
    for _, router in api._routers:
        route_keys.extend(router.path_operations.keys())

    assert "/dummy/" in route_keys
    assert "/dummy/{obj_id}/" in route_keys
    assert "/operations" in route_keys


def test_builder_cannot_initialize_twice():
    api = NinjaAPI()
    builder = ApplicationBuilder(api)

    builder.add_resource(
        path="/dummy",
        tags=["dummy"],
        resource_type="dummy",
        view=DummyView,
        model=DummyModel,
        schema=DummySchema,
        operations=[Operation.GET_LIST],
    )
    builder.initialize()

    with pytest.raises(ApplicationBuilderError):
        builder.initialize()


def test_builder_cannot_add_resource_after_initialize():
    api = NinjaAPI()
    builder = ApplicationBuilder(api)

    builder.add_resource(
        path="/dummy",
        tags=["dummy"],
        resource_type="dummy",
        view=DummyView,
        model=DummyModel,
        schema=DummySchema,
        operations=[Operation.GET_LIST],
    )
    builder.initialize()

    with pytest.raises(ApplicationBuilderError):
        builder.add_resource(
            path="/other",
            tags=["other"],
            resource_type="other",
            view=DummyView,
            model=DummyModel,
            schema=DummySchema,
            operations=[Operation.GET_LIST],
        )
