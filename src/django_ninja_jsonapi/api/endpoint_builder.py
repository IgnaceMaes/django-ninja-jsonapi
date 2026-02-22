import json
from typing import Any, Awaitable, Callable

from django.http import HttpRequest

from django_ninja_jsonapi.api.schemas import ResourceData
from django_ninja_jsonapi.exceptions import BadRequest
from django_ninja_jsonapi.views.enums import Operation


class EndpointsBuilder:
    def __init__(self, resource_type: str, data: ResourceData):
        self.resource_type = resource_type
        self.data = data

    def _build_view(self, request: HttpRequest, operation: Operation):
        return self.data.view(
            request=request,
            resource_type=self.resource_type,
            operation=operation,
            model=self.data.model,
            schema=self.data.source_schema,
        )

    @staticmethod
    def _parse_json_body(request: HttpRequest) -> dict[str, Any]:
        try:
            raw = request.body.decode() if request.body else "{}"
            return json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as ex:
            raise BadRequest(detail="Malformed JSON request body", parameter="body") from ex

    def create_common_ninja_endpoint(self, operation: Operation) -> tuple[str, Callable[..., Awaitable[Any]]]:
        if operation == Operation.GET:
            return self._create_get_detail()
        if operation == Operation.GET_LIST:
            return self._create_get_list()
        if operation == Operation.CREATE:
            return self._create_create()
        if operation == Operation.UPDATE:
            return self._create_update()
        if operation == Operation.DELETE:
            return self._create_delete()
        if operation == Operation.DELETE_LIST:
            return self._create_delete_list()

        raise ValueError(f"Unsupported operation {operation!r}")

    def create_relationship_endpoint(
        self,
        *,
        parent_resource_type: str,
        relationship_name: str,
        operation: Operation,
    ) -> tuple[str, Callable[..., Awaitable[Any]]]:
        if operation == Operation.GET_LIST:

            async def endpoint(request: HttpRequest, obj_id: str):
                view = self._build_view(request, operation)
                return await view.handle_get_resource_relationship_list(
                    obj_id=obj_id,
                    relationship_name=relationship_name,
                    parent_resource_type=parent_resource_type,
                )

            return f"{parent_resource_type}_{relationship_name}_get_list", endpoint

        async def endpoint(request: HttpRequest, obj_id: str):
            view = self._build_view(request, operation)
            return await view.handle_get_resource_relationship(
                obj_id=obj_id,
                relationship_name=relationship_name,
                parent_resource_type=parent_resource_type,
            )

        return f"{parent_resource_type}_{relationship_name}_get", endpoint

    def _create_get_detail(self):
        async def endpoint(request: HttpRequest, obj_id: str):
            view = self._build_view(request, Operation.GET)
            return await view.handle_get_resource_detail(obj_id=obj_id)

        return f"{self.resource_type}_get", endpoint

    def _create_get_list(self):
        async def endpoint(request: HttpRequest):
            view = self._build_view(request, Operation.GET_LIST)
            return await view.handle_get_resource_list()

        return f"{self.resource_type}_get_list", endpoint

    def _create_create(self):
        async def endpoint(request: HttpRequest):
            view = self._build_view(request, Operation.CREATE)
            payload = self.data.schema_in_post_data.model_validate(self._parse_json_body(request))
            return await view.handle_post_resource_list(data_create=payload.data)

        return f"{self.resource_type}_create", endpoint

    def _create_update(self):
        async def endpoint(request: HttpRequest, obj_id: str):
            view = self._build_view(request, Operation.UPDATE)
            payload = self.data.schema_in_patch_data.model_validate(self._parse_json_body(request))
            return await view.handle_update_resource(obj_id=obj_id, data_update=payload.data)

        return f"{self.resource_type}_update", endpoint

    def _create_delete(self):
        async def endpoint(request: HttpRequest, obj_id: str):
            view = self._build_view(request, Operation.DELETE)
            await view.handle_delete_resource(obj_id=obj_id)
            return 204, None

        return f"{self.resource_type}_delete", endpoint

    def _create_delete_list(self):
        async def endpoint(request: HttpRequest):
            view = self._build_view(request, Operation.DELETE_LIST)
            return await view.handle_delete_resource_list()

        return f"{self.resource_type}_delete_list", endpoint
