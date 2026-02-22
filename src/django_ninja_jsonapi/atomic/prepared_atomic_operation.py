from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional, Type

from django.http import HttpRequest

from django_ninja_jsonapi.atomic.schemas import AtomicOperationAction, AtomicOperationRef, OperationDataType
from django_ninja_jsonapi.data_layers.base import BaseDataLayer
from django_ninja_jsonapi.data_typing import TypeSchema
from django_ninja_jsonapi.storages import models_storage, schemas_storage, views_storage
from django_ninja_jsonapi.views import Operation, OperationConfig, ViewBase

LocalIdsType = dict[str, dict[str, str]]
atomic_dependency_handlers: dict[(str, Operation), Callable] = {}


@dataclass
class OperationBase:
    view: ViewBase
    ref: Optional[AtomicOperationRef]
    data: OperationDataType
    op_type: str
    resource_type: str

    @classmethod
    def prepare(
        cls,
        action: str,
        request: HttpRequest,
        resource_type: str,
        ref: Optional[AtomicOperationRef],
        data: OperationDataType,
    ) -> OperationBase:
        view_cls: Type[ViewBase] = views_storage.get_view(resource_type)

        if hasattr(action, "value"):
            # convert to str if enum
            action = action.value

        if action == AtomicOperationAction.add:
            operation_cls = OperationAdd
            view_operation = Operation.CREATE
        elif action == AtomicOperationAction.update:
            operation_cls = OperationUpdate
            view_operation = Operation.UPDATE
        elif action == AtomicOperationAction.remove:
            operation_cls = OperationRemove
            view_operation = Operation.DELETE
        else:
            msg = f"Unknown operation {action!r}"
            raise ValueError(msg)

        view = view_cls(
            request=request,
            resource_type=resource_type,
            operation=view_operation,
            model=models_storage.get_model(resource_type),
            schema=schemas_storage.get_source_schema(resource_type),
        )

        return operation_cls(
            view=view,
            ref=ref,
            data=data,
            op_type=action,
            resource_type=resource_type,
        )

    @classmethod
    async def handle_view_dependencies(
        cls,
        request: HttpRequest,
        view_cls: Type[ViewBase],
        resource_type: str,
        operation: Operation,
    ) -> dict[str, Any]:
        """
        Combines all dependencies (prepared) and returns them as list

        Consider method config is already prepared for generic views
        Reuse the same config for atomic operations

        :param request:
        :param view_cls:
        :param resource_type:
        :param operation:
        :return:
        """
        handler_key = (resource_type, operation)

        if handler_key not in atomic_dependency_handlers:
            method_config: OperationConfig = view_cls.operation_dependencies.get(operation) or OperationConfig()

            def handle_dependencies() -> dict[str, Any]:
                if method_config.dependencies is None:
                    return {}

                dep_model = method_config.dependencies
                if dep_model is None:
                    return {}

                return dep_model().model_dump()

            atomic_dependency_handlers[handler_key] = handle_dependencies

        return atomic_dependency_handlers[handler_key]()

    async def get_data_layer(self) -> BaseDataLayer:
        data_layer_view_dependencies: dict[str, Any] = await self.handle_view_dependencies(
            request=self.view.request,
            view_cls=self.view.__class__,
            resource_type=self.resource_type,
            operation=self.view.operation,
        )
        return await self.view.get_data_layer(data_layer_view_dependencies)

    async def handle(self, dl: BaseDataLayer) -> Optional[TypeSchema]:
        raise NotImplementedError

    @classmethod
    def upd_one_relationship_with_local_id(cls, relationship_info: dict, local_ids: LocalIdsType):
        """
        TODO: refactor

        :param relationship_info:
        :param local_ids:
        :return:
        """
        missing = object()
        lid = relationship_info.get("lid", missing)
        if lid is missing:
            return

        resource_type = relationship_info["type"]
        if resource_type not in local_ids:
            msg = (
                f"Resource {resource_type!r} not found in previous operations,"
                f" no lid {lid!r} defined yet, cannot create {relationship_info}"
            )
            raise ValueError(msg)

        lids_for_resource = local_ids[resource_type]
        if lid not in lids_for_resource:
            msg = (
                f"lid {lid!r} for {resource_type!r} not found in previous operations,"
                f" cannot process {relationship_info}"
            )
            raise ValueError(msg)

        relationship_info.pop("lid")
        relationship_info["id"] = lids_for_resource[lid]

    def update_relationships_with_lid(self, local_ids: LocalIdsType):
        if not (self.data and self.data.relationships):
            return
        for relationship_value in self.data.relationships.values():
            relationship_data = relationship_value["data"]
            if isinstance(relationship_data, list):
                for data in relationship_data:
                    self.upd_one_relationship_with_local_id(data, local_ids=local_ids)
            elif isinstance(relationship_data, dict):
                self.upd_one_relationship_with_local_id(relationship_data, local_ids=local_ids)
            else:
                msg = "unexpected relationship data"
                raise ValueError(msg)


class OperationAdd(OperationBase):
    async def handle(self, dl: BaseDataLayer) -> dict:
        # use outer schema wrapper because we need this error path:
        # `{'loc': ['data', 'attributes', 'name']`
        # and not `{'loc': ['attributes', 'name']`
        schema_in_create = schemas_storage.get_schema_in(self.resource_type, operation_type="create")
        data_in = schema_in_create(data=self.data.model_dump(exclude_unset=True))
        return await self.view.process_create_object(
            dl=dl,
            data_create=data_in.data,
        )


class OperationUpdate(OperationBase):
    async def handle(self, dl: BaseDataLayer) -> dict:
        if self.data is None:
            # TODO: clear to-one relationships
            pass
        # TODO: handle relationship update requests (relationship resources)

        # use outer schema wrapper because we need this error path:
        # `{'loc': ['data', 'attributes', 'name']`
        # and not `{'loc': ['attributes', 'name']`
        schema_in_update = schemas_storage.get_schema_in(self.resource_type, operation_type="create")
        data_in = schema_in_update(data=self.data.model_dump(exclude_unset=True))
        obj_id = (self.ref and self.ref.id) or (self.data and self.data.id)
        return await self.view.process_update_object(
            dl=dl,
            obj_id=obj_id,
            data_update=data_in.data,
        )


class OperationRemove(OperationBase):
    async def handle(
        self,
        dl: BaseDataLayer,
    ) -> None:
        """
        Calls view to delete object

        Todo: fix atomic delete
         Deleting Resources
           An operation that deletes a resource
           MUST target that resource
           through the operation’s ref or href members,
           but not both.

        :param dl:
        :return:
        """
        await self.view.process_delete_object(
            dl=dl,
            obj_id=self.ref and self.ref.id,
        )
