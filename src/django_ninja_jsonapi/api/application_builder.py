from http import HTTPStatus
from typing import Any, Callable, Iterable, Optional, Type

from ninja import NinjaAPI, Router
from pydantic import BaseModel

from django_ninja_jsonapi.api.endpoint_builder import EndpointsBuilder
from django_ninja_jsonapi.api.schemas import ResourceData
from django_ninja_jsonapi.atomic.atomic import AtomicOperations
from django_ninja_jsonapi.data_typing import TypeModel
from django_ninja_jsonapi.exceptions import HTTPException
from django_ninja_jsonapi.exceptions.handlers import base_exception_handler
from django_ninja_jsonapi.renderers import JSONAPIRenderer
from django_ninja_jsonapi.schema_builder import SchemaBuilder
from django_ninja_jsonapi.storages.models_storage import models_storage
from django_ninja_jsonapi.storages.schemas_storage import schemas_storage
from django_ninja_jsonapi.storages.views_storage import views_storage
from django_ninja_jsonapi.views.enums import Operation


class ApplicationBuilderError(Exception):
    pass


class ApplicationBuilder:
    def __init__(
        self,
        api: NinjaAPI,
        base_router: Optional[Router] = None,
        exception_handler: Optional[Callable] = None,
        **base_router_include_kwargs,
    ):
        self._api = api
        self._base_router = base_router or Router()
        self._base_router_include_kwargs = base_router_include_kwargs
        self._routers: dict[str, Router] = {}
        self._router_include_kwargs: dict[str, dict[str, Any]] = {}
        self._resource_data: dict[str, ResourceData] = {}
        self._exception_handler: Callable = exception_handler or base_exception_handler
        self._initialized = False
        self._api.renderer = JSONAPIRenderer()

    def add_resource(
        self,
        path: str,
        tags: Iterable[str],
        resource_type: str,
        view: Type[Any],
        model: Type[TypeModel],
        schema: Type[BaseModel],
        router: Optional[Router] = None,
        schema_in_post: Optional[Type[BaseModel]] = None,
        schema_in_patch: Optional[Type[BaseModel]] = None,
        pagination_default_size: Optional[int] = 20,
        pagination_default_number: Optional[int] = 1,
        pagination_default_offset: Optional[int] = None,
        pagination_default_limit: Optional[int] = None,
        operations: Iterable[Operation] = (),
        ending_slash: bool = True,
        model_id_field_name: str = "id",
        include_router_kwargs: Optional[dict] = None,
    ):
        if self._initialized:
            raise ApplicationBuilderError("Can't add resource after app initialization")

        if resource_type in self._resource_data:
            raise ApplicationBuilderError(f"Resource {resource_type!r} already registered")

        if include_router_kwargs is not None and router is None:
            raise ApplicationBuilderError(
                "The argument 'include_router_kwargs' is not allowed when 'router' is missing"
            )

        models_storage.add_model(resource_type, model, model_id_field_name, path)
        views_storage.add_view(resource_type, view)

        dto = SchemaBuilder(resource_type).create_schemas(
            schema=schema,
            schema_in_post=schema_in_post,
            schema_in_patch=schema_in_patch,
        )

        resource_operations = list(operations) or Operation.real_operations()
        if Operation.ALL in resource_operations:
            resource_operations = Operation.real_operations()

        self._resource_data[resource_type] = ResourceData(
            path=path,
            tags=list(tags),
            view=view,
            model=model,
            source_schema=schema,
            schema_in_post=schema_in_post,
            schema_in_post_data=dto.schema_in_post_data,
            schema_in_patch=schema_in_patch,
            schema_in_patch_data=dto.schema_in_patch_data,
            detail_response_schema=dto.detail_response_schema,
            list_response_schema=dto.list_response_schema,
            pagination_default_size=pagination_default_size,
            pagination_default_number=pagination_default_number,
            pagination_default_offset=pagination_default_offset,
            pagination_default_limit=pagination_default_limit,
            operations=resource_operations,
            ending_slash=ending_slash,
        )

        resolved_router = router or self._base_router
        self._routers[resource_type] = resolved_router
        self._router_include_kwargs[resource_type] = include_router_kwargs or {}

    def initialize(self) -> NinjaAPI:
        if self._initialized:
            raise ApplicationBuilderError("Application already initialized")

        self._initialized = True
        self._register_exception_handler()

        for resource_type, data in self._resource_data.items():
            builder = EndpointsBuilder(resource_type, data)
            router = self._routers[resource_type]

            for operation in data.operations:
                name, endpoint = builder.create_common_ninja_endpoint(operation)
                method = operation.http_method().lower()
                path = self._create_path(
                    path=data.path,
                    include_object_id=operation in {Operation.GET, Operation.UPDATE, Operation.DELETE},
                    ending_slash=data.ending_slash,
                )

                response_schema = self._response_for(data, operation)
                route = getattr(router, method)
                route(
                    path,
                    response=response_schema,
                    tags=data.tags,
                    operation_id=name,
                )(endpoint)

            relationships_info = schemas_storage.get_relationships_info(
                resource_type=resource_type,
                operation_type="get",
            )
            for relationship_name, info in relationships_info.items():
                if not views_storage.has_view(info.resource_type):
                    continue

                operation = Operation.GET_LIST if info.many else Operation.GET
                relationship_builder = EndpointsBuilder(info.resource_type, self._resource_data.get(info.resource_type, data))
                relationship_name_id, relationship_endpoint = relationship_builder.create_relationship_endpoint(
                    parent_resource_type=resource_type,
                    relationship_name=relationship_name,
                    operation=operation,
                )
                relationship_path = self._create_relationship_path(
                    resource_path=data.path,
                    relationship_name=relationship_name,
                    ending_slash=data.ending_slash,
                )

                related_data = self._resource_data.get(info.resource_type, data)
                relationship_response = (
                    related_data.list_response_schema if info.many else related_data.detail_response_schema
                )
                getattr(router, operation.http_method().lower())(
                    relationship_path,
                    response=relationship_response,
                    tags=data.tags,
                    operation_id=relationship_name_id,
                )(relationship_endpoint)

        registered_routers = set()
        for resource_type, router in self._routers.items():
            if id(router) in registered_routers:
                continue

            include_kwargs = self._router_include_kwargs.get(resource_type, {})
            if router is self._base_router:
                include_kwargs = self._base_router_include_kwargs

            self._api.add_router("", router, **include_kwargs)
            registered_routers.add(id(router))

        atomic = AtomicOperations()
        self._api.add_router("", atomic.router)

        return self._api

    def _register_exception_handler(self):
        add_handler = getattr(self._api, "add_exception_handler", None)
        if callable(add_handler):
            add_handler(HTTPException, self._exception_handler)

    @staticmethod
    def _response_for(data: ResourceData, operation: Operation):
        if operation == Operation.DELETE:
            return {HTTPStatus.NO_CONTENT: None}
        if operation == Operation.GET_LIST:
            return data.list_response_schema
        return data.detail_response_schema

    @staticmethod
    def _create_path(path: str, include_object_id: bool, ending_slash: bool) -> str:
        base_path = path.rstrip("/")
        if include_object_id:
            base_path = f"{base_path}/{{obj_id}}"
        if ending_slash:
            return f"{base_path}/"
        return base_path

    @staticmethod
    def _create_relationship_path(resource_path: str, relationship_name: str, ending_slash: bool) -> str:
        base_path = resource_path.rstrip("/")
        path = f"{base_path}/{{obj_id}}/relationships/{relationship_name}"
        if ending_slash:
            return f"{path}/"
        return path
