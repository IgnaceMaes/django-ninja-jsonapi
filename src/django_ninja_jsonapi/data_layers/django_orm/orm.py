from __future__ import annotations

from typing import Optional

from asgiref.sync import sync_to_async
from django.db import transaction

from django_ninja_jsonapi.common import get_relationship_info_from_field_metadata
from django_ninja_jsonapi.data_layers.base import BaseDataLayer
from django_ninja_jsonapi.data_layers.django_orm.base_model import BaseDjangoORM
from django_ninja_jsonapi.data_layers.django_orm.query_building import apply_filters, apply_sorts
from django_ninja_jsonapi.exceptions import InvalidInclude, RelationNotFound
from django_ninja_jsonapi.querystring import QueryStringManager
from django_ninja_jsonapi.schema import BaseJSONAPIItemInSchema
from django_ninja_jsonapi.storages.models_storage import models_storage
from django_ninja_jsonapi.storages.schemas_storage import schemas_storage
from django_ninja_jsonapi.views.schemas import RelationshipRequestInfo


class DjangoORMDataLayer(BaseDataLayer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._atomic_ctx: Optional[transaction.Atomic] = None

    async def atomic_start(self, previous_dl: Optional[BaseDataLayer] = None):
        await super().atomic_start(previous_dl)
        if (
            previous_dl is not None
            and isinstance(previous_dl, DjangoORMDataLayer)
            and previous_dl._atomic_ctx is not None
        ):
            self._atomic_ctx = previous_dl._atomic_ctx
            return

        self._atomic_ctx = transaction.atomic()
        await sync_to_async(self._atomic_ctx.__enter__, thread_sensitive=True)()

    async def atomic_end(self, success: bool = True, exception: Optional[Exception] = None):
        if self._atomic_ctx is None:
            return

        exc_type = type(exception) if exception is not None else None
        await sync_to_async(self._atomic_ctx.__exit__, thread_sensitive=True)(exc_type, exception, None)
        self._atomic_ctx = None

    async def create_object(self, data_create: BaseJSONAPIItemInSchema, view_kwargs: dict):
        await self.before_create_object(data_create, view_kwargs)

        model_kwargs = data_create.attributes.model_dump(exclude_unset=True)
        model_kwargs = self._apply_client_generated_id(data_create, model_kwargs)

        db_object = await sync_to_async(BaseDjangoORM.create, thread_sensitive=True)(self.model, **model_kwargs)
        atomic_ctx = await self._start_nested_atomic()
        try:
            await self._apply_relationships(db_object, data_create)
        except Exception as ex:
            await self._end_nested_atomic(atomic_ctx, exception=ex)
            raise
        await self._end_nested_atomic(atomic_ctx)

        await self.after_create_object(db_object, data_create, view_kwargs)
        return db_object

    async def get_object(
        self,
        view_kwargs: dict,
        qs: Optional[QueryStringManager] = None,
        relationship_request_info: Optional[RelationshipRequestInfo] = None,
    ):
        await self.before_get_object(view_kwargs)

        queryset = BaseDjangoORM.queryset(self.model)
        if qs is not None:
            queryset = self._apply_querystring(queryset, qs)

        if relationship_request_info is not None:
            parent_model = models_storage.get_model(relationship_request_info.parent_resource_type)
            parent_obj = await sync_to_async(BaseDjangoORM.one_or_raise, thread_sensitive=True)(
                BaseDjangoORM.queryset(parent_model),
                **{
                    models_storage.get_model_id_field_name(
                        relationship_request_info.parent_resource_type
                    ): relationship_request_info.parent_obj_id
                },
            )
            relationship_name = relationship_request_info.relationship_name
            relationship_info = schemas_storage.get_relationship_info(
                resource_type=relationship_request_info.parent_resource_type,
                operation_type="get",
                field_name=relationship_name,
            )
            relation_attr_name = (
                relationship_info.model_field_name
                if relationship_info and relationship_info.model_field_name
                else relationship_name
            )
            relationship_value = getattr(parent_obj, relationship_name, None)
            if relationship_value is None and relation_attr_name != relationship_name:
                relationship_value = getattr(parent_obj, relation_attr_name, None)
            if relationship_value is None:
                raise RelationNotFound(detail=f"Relation {relationship_name!r} not found")

            if hasattr(relationship_value, "all"):
                related_ids = await sync_to_async(
                    lambda: list(relationship_value.values_list("pk", flat=True)), thread_sensitive=True
                )()
                queryset = queryset.filter(pk__in=related_ids)
            else:
                queryset = queryset.filter(pk=getattr(relationship_value, "pk", None))

        db_object = await sync_to_async(BaseDjangoORM.one_or_raise, thread_sensitive=True)(queryset, **view_kwargs)
        await self.after_get_object(db_object, view_kwargs)
        return db_object

    async def get_collection(
        self,
        qs: QueryStringManager,
        view_kwargs: Optional[dict] = None,
        relationship_request_info: Optional[RelationshipRequestInfo] = None,
    ):
        await self.before_get_collection(qs, view_kwargs)

        queryset = BaseDjangoORM.queryset(self.model)
        if view_kwargs:
            queryset = queryset.filter(**view_kwargs)

        queryset = self._apply_querystring(queryset, qs)

        if relationship_request_info is not None:
            parent_model = models_storage.get_model(relationship_request_info.parent_resource_type)
            parent_obj = await sync_to_async(BaseDjangoORM.one_or_raise, thread_sensitive=True)(
                BaseDjangoORM.queryset(parent_model),
                **{
                    models_storage.get_model_id_field_name(
                        relationship_request_info.parent_resource_type
                    ): relationship_request_info.parent_obj_id
                },
            )
            relationship_info = schemas_storage.get_relationship_info(
                resource_type=relationship_request_info.parent_resource_type,
                operation_type="get",
                field_name=relationship_request_info.relationship_name,
            )
            relation_attr_name = (
                relationship_info.model_field_name
                if relationship_info and relationship_info.model_field_name
                else relationship_request_info.relationship_name
            )
            relationship_value = getattr(parent_obj, relationship_request_info.relationship_name, None)
            if relationship_value is None and relation_attr_name != relationship_request_info.relationship_name:
                relationship_value = getattr(parent_obj, relation_attr_name, None)
            if relationship_value is None:
                raise RelationNotFound(detail=f"Relation {relationship_request_info.relationship_name!r} not found")

            if hasattr(relationship_value, "all"):
                related_ids = await sync_to_async(
                    lambda: list(relationship_value.values_list("pk", flat=True)), thread_sensitive=True
                )()
                queryset = queryset.filter(pk__in=related_ids)
            else:
                queryset = queryset.filter(pk=getattr(relationship_value, "pk", None))

        count = self.default_collection_count
        if not self.disable_collection_count:
            count = await sync_to_async(queryset.count, thread_sensitive=True)()

        paged_queryset = queryset
        if qs.pagination.size:
            page_number = max(1, qs.pagination.number)
            offset = (page_number - 1) * qs.pagination.size
            paged_queryset = queryset[offset : offset + qs.pagination.size]
        elif qs.pagination.offset is not None and qs.pagination.limit is not None:
            paged_queryset = queryset[qs.pagination.offset : qs.pagination.offset + qs.pagination.limit]

        items = await sync_to_async(list, thread_sensitive=True)(paged_queryset)
        await self.after_get_collection(items, qs, view_kwargs)
        return count, items

    async def update_object(self, obj, data_update: BaseJSONAPIItemInSchema, view_kwargs: dict):
        await self.before_update_object(obj, data_update, view_kwargs)

        model_kwargs = data_update.attributes.model_dump(exclude_unset=True)
        atomic_ctx = await self._start_nested_atomic()
        try:
            await sync_to_async(BaseDjangoORM.update, thread_sensitive=True)(obj, **model_kwargs)
            await self._apply_relationships(obj, data_update)
        except Exception as ex:
            await self._end_nested_atomic(atomic_ctx, exception=ex)
            raise
        await self._end_nested_atomic(atomic_ctx)

        await self.after_update_object(obj, data_update, view_kwargs)
        return obj

    async def delete_object(self, obj, view_kwargs):
        await self.before_delete_object(obj, view_kwargs)
        await sync_to_async(BaseDjangoORM.delete, thread_sensitive=True)(obj)
        await self.after_delete_object(obj, view_kwargs)

    async def delete_objects(self, objects, view_kwargs):
        if not objects:
            return

        if self._has_custom_delete_hooks():
            for obj in objects:
                await self.delete_object(obj, view_kwargs)
            return

        id_field_name = models_storage.get_model_id_field_name(self.resource_type)
        object_ids = [getattr(obj, id_field_name) for obj in objects]
        queryset = BaseDjangoORM.queryset(self.model).filter(**{f"{id_field_name}__in": object_ids})
        await sync_to_async(queryset.delete, thread_sensitive=True)()

    @classmethod
    def _is_overridden(cls, method_name: str, method) -> bool:
        method_func = getattr(method, "__func__", method)
        return method_func is not getattr(cls, method_name)

    def _has_custom_delete_hooks(self) -> bool:
        return any(
            [
                self._is_overridden("before_delete_object", self.before_delete_object),
                self._is_overridden("after_delete_object", self.after_delete_object),
            ]
        )

    async def _start_nested_atomic(self) -> Optional[transaction.Atomic]:
        if self._atomic_ctx is not None:
            return None

        atomic_ctx = transaction.atomic()
        await sync_to_async(atomic_ctx.__enter__, thread_sensitive=True)()
        return atomic_ctx

    async def _end_nested_atomic(self, atomic_ctx: Optional[transaction.Atomic], exception: Optional[Exception] = None):
        if atomic_ctx is None:
            return

        exc_type = type(exception) if exception is not None else None
        await sync_to_async(atomic_ctx.__exit__, thread_sensitive=True)(exc_type, exception, None)

    async def create_relationship(self, json_data, relationship_field, related_id_field, view_kwargs):
        return await self.update_relationship(json_data, relationship_field, related_id_field, view_kwargs)

    async def get_relationship(self, relationship_field, related_type_, related_id_field, view_kwargs):
        db_object = await self.get_object(view_kwargs=view_kwargs)
        field = self.schema.model_fields.get(relationship_field)
        rel_info = get_relationship_info_from_field_metadata(field) if field is not None else None
        relation_attr_name = rel_info.model_field_name if rel_info and rel_info.model_field_name else relationship_field
        relationship = getattr(db_object, relation_attr_name)
        if hasattr(relationship, "all"):
            related_objects = await sync_to_async(list, thread_sensitive=True)(relationship.all())
        else:
            related_objects = [relationship] if relationship is not None else []

        return db_object, related_objects

    async def update_relationship(self, json_data, relationship_field, related_id_field, view_kwargs):
        db_object = await self.get_object(view_kwargs=view_kwargs)
        field = self.schema.model_fields.get(relationship_field)
        rel_info = get_relationship_info_from_field_metadata(field) if field is not None else None
        relation_attr_name = rel_info.model_field_name if rel_info and rel_info.model_field_name else relationship_field
        relationship = getattr(db_object, relation_attr_name)

        items = json_data.get("data") or []
        if isinstance(items, dict):
            items = [items]

        ids = [item["id"] for item in items]
        related_model = models_storage.search_relationship_model(self.resource_type, self.model, relation_attr_name)
        related_objects = await self.get_related_objects(related_model, related_id_field, ids)

        if hasattr(relationship, "set"):
            await sync_to_async(relationship.set, thread_sensitive=True)(related_objects)
        else:
            value = related_objects[0] if related_objects else None
            setattr(db_object, relation_attr_name, value)
            await sync_to_async(db_object.save, thread_sensitive=True)()

        return True

    async def delete_relationship(self, json_data, relationship_field, related_id_field, view_kwargs):
        db_object = await self.get_object(view_kwargs=view_kwargs)
        field = self.schema.model_fields.get(relationship_field)
        rel_info = get_relationship_info_from_field_metadata(field) if field is not None else None
        relation_attr_name = rel_info.model_field_name if rel_info and rel_info.model_field_name else relationship_field
        relationship = getattr(db_object, relation_attr_name)

        items = json_data.get("data") or []
        if isinstance(items, dict):
            items = [items]

        ids = [item["id"] for item in items]
        related_model = models_storage.search_relationship_model(self.resource_type, self.model, relation_attr_name)
        related_objects = await self.get_related_objects(related_model, related_id_field, ids)

        if hasattr(relationship, "remove"):
            await sync_to_async(relationship.remove, thread_sensitive=True)(*related_objects)
        else:
            setattr(db_object, relation_attr_name, None)
            await sync_to_async(db_object.save, thread_sensitive=True)()

        return True

    async def get_related_objects(self, related_model, related_id_field: str, ids: list[str]):
        queryset = BaseDjangoORM.queryset(related_model).filter(**{f"{related_id_field}__in": ids})
        return await sync_to_async(list, thread_sensitive=True)(queryset)

    def _apply_querystring(self, queryset, qs: QueryStringManager):
        queryset = apply_filters(queryset, qs.filters)
        queryset = apply_sorts(queryset, qs.sorts)

        for include_path in qs.include:
            include_expr = self._map_include_path_to_prefetch(include_path)
            queryset = queryset.prefetch_related(include_expr)

        fields = qs.fields.get(self.resource_type)
        if fields:
            queryset = queryset.only(models_storage.get_model_id_field_name(self.resource_type), *fields)

        return queryset

    def _map_include_path_to_prefetch(self, include_path: str) -> str:
        resource_type = self.resource_type
        include_expr_parts = []

        for relationship_name in include_path.split("."):
            relationship_info = schemas_storage.get_relationship_info(
                resource_type=resource_type,
                operation_type="get",
                field_name=relationship_name,
            )
            if relationship_info is None:
                raise InvalidInclude(
                    detail=(f"Relationship {relationship_name!r} is not available for resource type {resource_type!r}.")
                )

            include_expr_parts.append(relationship_info.model_field_name or relationship_name)
            resource_type = relationship_info.resource_type

        return "__".join(include_expr_parts)

    async def _apply_relationships(self, db_object, data_payload: BaseJSONAPIItemInSchema):
        if data_payload.relationships is None:
            return

        relationships_data = data_payload.relationships.model_dump(exclude_none=True)
        for relation_name, rel_payload in relationships_data.items():
            if "data" not in rel_payload:
                continue

            field = self.schema.model_fields.get(relation_name)
            if field is None:
                continue

            rel_info = get_relationship_info_from_field_metadata(field)
            if rel_info is None:
                continue

            ids_payload = rel_payload["data"]
            if rel_info.many:
                ids = [item["id"] for item in ids_payload]
            else:
                ids = [ids_payload["id"]] if ids_payload else []

            relation_attr_name = rel_info.model_field_name or relation_name
            related_model = models_storage.search_relationship_model(self.resource_type, self.model, relation_attr_name)
            related_objects = await self.get_related_objects(related_model, rel_info.id_field_name, ids)

            relation_attr = getattr(db_object, relation_attr_name)
            if hasattr(relation_attr, "set"):
                await sync_to_async(relation_attr.set, thread_sensitive=True)(related_objects)
            else:
                value = related_objects[0] if related_objects else None
                setattr(db_object, relation_attr_name, value)
                await sync_to_async(db_object.save, thread_sensitive=True)()

    async def before_create_object(self, data, view_kwargs):
        return None

    async def after_create_object(self, obj, data, view_kwargs):
        return None

    async def before_get_object(self, view_kwargs):
        return None

    async def after_get_object(self, obj, view_kwargs):
        return None

    async def before_get_collection(self, qs, view_kwargs):
        return None

    async def after_get_collection(self, objs, qs, view_kwargs):
        return None

    async def before_update_object(self, obj, data, view_kwargs):
        return None

    async def after_update_object(self, obj, data, view_kwargs):
        return None

    async def before_delete_object(self, obj, view_kwargs):
        return None

    async def after_delete_object(self, obj, view_kwargs):
        return None
