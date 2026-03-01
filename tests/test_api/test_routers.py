from typing import Annotated

import pytest
from ninja import NinjaAPI
from pydantic import BaseModel

from django_ninja_jsonapi.api.application_builder import ApplicationBuilder, ApplicationBuilderError
from django_ninja_jsonapi.types_metadata import RelationshipInfo
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
        return {"data": {"type": "dummy", "id": "1", "attributes": {"name": "x"}}}

    async def handle_update_resource(self, obj_id: str, data_update):
        return {"data": {"type": "dummy", "id": obj_id, "attributes": {"name": "x"}}}

    async def handle_delete_resource(self, obj_id: str):
        return None


def _collect_path_methods(api: NinjaAPI) -> dict[str, set[str]]:
    path_methods: dict[str, set[str]] = {}
    for _, router in api._routers:
        for path, path_view in router.path_operations.items():
            methods: set[str] = set()
            for operation in path_view.operations:
                if hasattr(operation, "methods"):
                    methods.update(method.upper() for method in operation.methods)
                elif hasattr(operation, "method"):
                    methods.add(str(operation.method).upper())
            path_methods[path] = path_methods.get(path, set()).union(methods)

    return path_methods


def test_limited_operations_register_only_requested_http_methods():
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
    builder.initialize()

    path_methods = _collect_path_methods(api)

    assert path_methods["/dummy/"] == {"GET"}
    assert path_methods["/dummy/{obj_id}/"] == {"GET"}


def test_default_operations_do_not_register_delete_on_list_route():
    api = NinjaAPI()
    builder = ApplicationBuilder(api)

    builder.add_resource(
        path="/dummy",
        tags=["dummy"],
        resource_type="dummy",
        view=DummyView,
        model=DummyModel,
        schema=DummySchema,
    )
    builder.initialize()

    path_methods = _collect_path_methods(api)

    assert "DELETE" not in path_methods["/dummy/"]


def test_resource_registration_guards_duplicate_resource_type():
    api = NinjaAPI()
    builder = ApplicationBuilder(api)

    builder.add_resource(
        path="/users",
        tags=["users"],
        resource_type="user",
        view=DummyView,
        model=DummyModel,
        schema=DummySchema,
    )

    with pytest.raises(ApplicationBuilderError):
        builder.add_resource(
            path="/users-2",
            tags=["users"],
            resource_type="user",
            view=DummyView,
            model=DummyModel,
            schema=DummySchema,
        )


def test_include_router_kwargs_requires_router_argument():
    api = NinjaAPI()
    builder = ApplicationBuilder(api)

    with pytest.raises(ApplicationBuilderError):
        builder.add_resource(
            path="/users",
            tags=["users"],
            resource_type="user",
            view=DummyView,
            model=DummyModel,
            schema=DummySchema,
            include_router_kwargs={"prefix": "/v1"},
        )


def test_to_many_relationship_registers_mutation_routes():
    """POST, PATCH, DELETE mutation routes are auto-registered for to-many relationships."""

    class ComputerSchema(BaseModel):
        id: int
        serial: str

    class CustomerSchema(BaseModel):
        id: int
        name: str
        computers: Annotated[list[ComputerSchema], RelationshipInfo(resource_type="computer", many=True)] = []

    api = NinjaAPI()
    builder = ApplicationBuilder(api)

    builder.add_resource(
        path="/customers",
        tags=["customers"],
        resource_type="customer",
        view=DummyView,
        model=DummyModel,
        schema=CustomerSchema,
    )
    builder.add_resource(
        path="/computers",
        tags=["computers"],
        resource_type="computer",
        view=DummyView,
        model=DummyModel,
        schema=ComputerSchema,
    )

    builder.initialize()

    path_methods = _collect_path_methods(api)
    rel_path = "/customers/{obj_id}/relationships/computers/"
    assert rel_path in path_methods
    assert {"GET", "POST", "PATCH", "DELETE"} == path_methods[rel_path]


def test_to_one_relationship_registers_only_patch_mutation():
    """Only PATCH mutation route is auto-registered for to-one relationships."""

    class AddressSchema(BaseModel):
        id: int
        street: str

    class PersonSchema(BaseModel):
        id: int
        name: str
        address: Annotated[AddressSchema, RelationshipInfo(resource_type="address", many=False)]

    api = NinjaAPI()
    builder = ApplicationBuilder(api)

    builder.add_resource(
        path="/people",
        tags=["people"],
        resource_type="person",
        view=DummyView,
        model=DummyModel,
        schema=PersonSchema,
    )
    builder.add_resource(
        path="/addresses",
        tags=["addresses"],
        resource_type="address",
        view=DummyView,
        model=DummyModel,
        schema=AddressSchema,
    )

    builder.initialize()

    path_methods = _collect_path_methods(api)
    rel_path = "/people/{obj_id}/relationships/address/"
    assert rel_path in path_methods
    # to-one: GET + PATCH only (no POST, no DELETE)
    assert {"GET", "PATCH"} == path_methods[rel_path]


def test_relationship_mutation_operation_ids():
    """Verify that mutation endpoints get correct operation IDs."""

    class TagSchema(BaseModel):
        id: int
        label: str

    class ArticleSchema(BaseModel):
        id: int
        title: str
        tags: Annotated[list[TagSchema], RelationshipInfo(resource_type="tag", many=True)] = []

    api = NinjaAPI()
    builder = ApplicationBuilder(api)

    builder.add_resource(
        path="/articles",
        tags=["articles"],
        resource_type="article",
        view=DummyView,
        model=DummyModel,
        schema=ArticleSchema,
    )
    builder.add_resource(
        path="/tags",
        tags=["tags"],
        resource_type="tag",
        view=DummyView,
        model=DummyModel,
        schema=TagSchema,
    )

    builder.initialize()

    operation_ids = set()
    for _, router in api._routers:
        path_view = router.path_operations.get("/articles/{obj_id}/relationships/tags/")
        if path_view:
            for op in path_view.operations:
                if hasattr(op, "operation_id"):
                    operation_ids.add(op.operation_id)

    assert "article_tags_get_list" in operation_ids
    assert "article_tags_create" in operation_ids
    assert "article_tags_update" in operation_ids
    assert "article_tags_delete" in operation_ids


def test_relationship_endpoint_uses_related_resource_builder_context():
    class ComputerSchema(BaseModel):
        id: int
        serial: str

    class CustomerSchema(BaseModel):
        id: int
        name: str
        computers: Annotated[list[ComputerSchema], RelationshipInfo(resource_type="computer", many=True)] = []

    api = NinjaAPI()
    builder = ApplicationBuilder(api)

    builder.add_resource(
        path="/customers",
        tags=["customers"],
        resource_type="customer",
        view=DummyView,
        model=DummyModel,
        schema=CustomerSchema,
    )
    builder.add_resource(
        path="/computers",
        tags=["computers"],
        resource_type="computer",
        view=DummyView,
        model=DummyModel,
        schema=ComputerSchema,
    )

    builder.initialize()

    relationship_op = None
    for _, router in api._routers:
        path_view = router.path_operations.get("/customers/{obj_id}/relationships/computers/")
        if not path_view:
            continue

        relationship_op = next(
            (op for op in path_view.operations if getattr(op, "operation_id", "") == "customer_computers_get_list"),
            None,
        )
        if relationship_op:
            break

    assert relationship_op is not None
    closure = getattr(relationship_op.view_func, "__closure__", ()) or ()
    captured_resource_types = [
        cell.cell_contents.resource_type for cell in closure if hasattr(cell.cell_contents, "resource_type")
    ]

    assert "computer" in captured_resource_types
