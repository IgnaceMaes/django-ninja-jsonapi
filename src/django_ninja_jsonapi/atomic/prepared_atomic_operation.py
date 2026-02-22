from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Type

from django.http import HttpRequest

from django_ninja_jsonapi.atomic.schemas import (
    AtomicOperationAction,
    AtomicOperationRef,
    OperationDataType,
    OperationItemInSchema,
    OperationRelationshipSchema,
)
from django_ninja_jsonapi.data_layers.base import BaseDataLayer
from django_ninja_jsonapi.data_typing import TypeSchema
from django_ninja_jsonapi.storages import models_storage, schemas_storage, views_storage
from django_ninja_jsonapi.views import Operation, OperationConfig, ViewBase

LocalIdsType = dict[str, dict[str, str]]
atomic_dependency_handlers: dict[(str, Operation), dict[str, Any]] = {}


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

        if handler_key in atomic_dependency_handlers:
            return atomic_dependency_handlers[handler_key]

        merged_defaults: dict[str, Any] = {}
        dependency_configs = [
            view_cls.operation_dependencies.get(Operation.ALL),
            view_cls.operation_dependencies.get(operation),
        ]
        for method_config in dependency_configs:
            if method_config is None:
                continue

            if not isinstance(method_config, OperationConfig) or method_config.dependencies is None:
                continue

            merged_defaults.update(method_config.dependencies().model_dump())

        atomic_dependency_handlers[handler_key] = merged_defaults
        return merged_defaults

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

    @classmethod
    def _replace_lid_with_id(
        cls,
        *,
        resource_type: str,
        lid: str,
        local_ids: LocalIdsType,
    ) -> str:
        if resource_type not in local_ids:
            msg = f"Resource {resource_type!r} not found in previous operations for lid {lid!r}."
            raise ValueError(msg)

        resource_local_ids = local_ids[resource_type]
        if lid not in resource_local_ids:
            msg = f"lid {lid!r} for {resource_type!r} not found in previous operations."
            raise ValueError(msg)

        return resource_local_ids[lid]

    @classmethod
    def _update_relationship_lid_model(
        cls,
        relationship_data: OperationRelationshipSchema,
        local_ids: LocalIdsType,
    ):
        if relationship_data.lid is None:
            return

        relationship_data.id = cls._replace_lid_with_id(
            resource_type=relationship_data.type,
            lid=relationship_data.lid,
            local_ids=local_ids,
        )
        relationship_data.lid = None

    def update_relationships_with_lid(self, local_ids: LocalIdsType):
        if self.ref is not None and self.ref.lid is not None:
            self.ref.id = self._replace_lid_with_id(
                resource_type=self.ref.type,
                lid=self.ref.lid,
                local_ids=local_ids,
            )
            self.ref.lid = None

        if isinstance(self.data, OperationRelationshipSchema):
            self._update_relationship_lid_model(self.data, local_ids)
            return

        if isinstance(self.data, list):
            for relationship_data in self.data:
                if isinstance(relationship_data, OperationRelationshipSchema):
                    self._update_relationship_lid_model(relationship_data, local_ids)
            return

        if not isinstance(self.data, OperationItemInSchema):
            return

        if self.data.lid is not None and self.data.id is None:
            self.data.id = self._replace_lid_with_id(
                resource_type=self.data.type,
                lid=self.data.lid,
                local_ids=local_ids,
            )
            self.data.lid = None

        if self.data.relationships is None:
            return

        for relationship_value in self.data.relationships.values():
            relationship_data = relationship_value["data"]
            if isinstance(relationship_data, list):
                for data in relationship_data:
                    self.upd_one_relationship_with_local_id(data, local_ids=local_ids)
            elif isinstance(relationship_data, dict):
                self.upd_one_relationship_with_local_id(relationship_data, local_ids=local_ids)
            elif relationship_data is None:
                continue
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
        obj_id = (self.ref and self.ref.id) or (self.data and getattr(self.data, "id", None))
        if obj_id is None:
            msg = "Object id is required for atomic update operation"
            raise ValueError(msg)

        if self.ref and self.ref.relationship:
            relationship_info = schemas_storage.get_relationship_info(
                resource_type=self.resource_type,
                operation_type="get",
                field_name=self.ref.relationship,
            )
            if relationship_info is None:
                msg = f"Relationship {self.ref.relationship!r} not found for {self.resource_type!r}"
                raise ValueError(msg)

            if self.data is not None and not isinstance(
                self.data,
                (OperationRelationshipSchema, list),
            ):
                msg = (
                    "Atomic relationship update expects relationship linkage data "
                    "(resource identifier object, list, or null)"
                )
                raise ValueError(msg)

            if isinstance(self.data, list):
                payload_data = [item.model_dump(exclude_none=True) for item in self.data]
            elif isinstance(self.data, OperationRelationshipSchema):
                payload_data = self.data.model_dump(exclude_none=True)
            elif self.data is None:
                payload_data = None
            else:
                payload_data = self.data.model_dump(exclude_none=True)

            await dl.update_relationship(
                json_data={"data": payload_data},
                relationship_field=self.ref.relationship,
                related_id_field=relationship_info.id_field_name,
                view_kwargs={dl.url_id_field: obj_id},
            )
            return await self.view.handle_get_resource_detail(obj_id=obj_id)

        if not isinstance(self.data, OperationItemInSchema):
            msg = "Atomic update for resource attributes expects resource object data"
            raise ValueError(msg)

        # use outer schema wrapper because we need this error path:
        # `{'loc': ['data', 'attributes', 'name']`
        # and not `{'loc': ['attributes', 'name']`
        schema_in_update = schemas_storage.get_schema_in(self.resource_type, operation_type="update")
        payload_data = self.data.model_dump(exclude_unset=True)
        payload_data.setdefault("id", obj_id)
        data_in = schema_in_update(data=payload_data)
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
        if self.ref is None or self.ref.id is None:
            msg = "Atomic remove operation requires target resource id in ref"
            raise ValueError(msg)

        await self.view.process_delete_object(
            dl=dl,
            obj_id=self.ref.id,
        )
