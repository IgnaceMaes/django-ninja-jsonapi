import asyncio
import inspect
import logging
from functools import partial
from typing import Any, Callable, ClassVar, Iterable, Optional, Type
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from django.http import HttpRequest as Request
from pydantic import BaseModel as PydanticBaseModel

from django_ninja_jsonapi.common import get_relationship_info_from_field_metadata
from django_ninja_jsonapi.data_layers.base import BaseDataLayer
from django_ninja_jsonapi.data_typing import TypeModel, TypeSchema
from django_ninja_jsonapi.exceptions import BadRequest, InvalidInclude
from django_ninja_jsonapi.inflection import format_keys
from django_ninja_jsonapi.inflection import get_formatter as get_inflection_formatter
from django_ninja_jsonapi.querystring import QueryStringManager
from django_ninja_jsonapi.schema import BaseJSONAPIItemInSchema
from django_ninja_jsonapi.schema_base import BaseModel
from django_ninja_jsonapi.storages.models_storage import models_storage
from django_ninja_jsonapi.storages.schemas_storage import schemas_storage
from django_ninja_jsonapi.types_metadata import RelationshipInfo
from django_ninja_jsonapi.views.enums import Operation
from django_ninja_jsonapi.views.schemas import OperationConfig, RelationshipRequestInfo

logger = logging.getLogger(__name__)


class ViewBase:
    """
    Views are inited for each request
    """

    data_layer_cls = BaseDataLayer
    operation_dependencies: ClassVar[dict[Operation, OperationConfig]] = {}
    select_for_includes: ClassVar[dict[str, list[str]]] = {}
    prefetch_for_includes: ClassVar[dict[str, list[str]]] = {}
    django_filterset_class: ClassVar[Optional[type]] = None

    def __init__(
        self,
        *,
        request: Request,
        resource_type: str,
        operation: Operation,
        model: Type[TypeModel],
        schema: Type[TypeSchema],
        **options,
    ):
        self.request: Request = request
        self.query_params: QueryStringManager
        self.resource_type: str = resource_type
        self.operation: Operation = operation
        self.model: Type[TypeModel] = model
        self.schema: Type[TypeSchema] = schema
        self.options: dict = options
        self.query_params: QueryStringManager = QueryStringManager(request=request)
        self.include_jsonapi_object: bool = self.query_params.config.get("INCLUDE_JSONAPI_OBJECT", False)
        self.jsonapi_version: str = str(self.query_params.config.get("JSONAPI_VERSION", "1.0"))
        self._api_prefix: Optional[str] = None
        self._validate_include_paths()

    async def get_data_layer(
        self,
        extra_view_deps: dict[str, Any],
    ) -> BaseDataLayer:
        """
        Prepares data layer for detail view

        :param extra_view_deps:
        :return:
        """
        dl_kwargs = await self.handle_endpoint_dependencies(extra_view_deps)
        return self.data_layer_cls(
            request=self.request,
            model=self.model,
            schema=self.schema,
            resource_type=self.resource_type,
            select_for_includes=self.select_for_includes,
            prefetch_for_includes=self.prefetch_for_includes,
            django_filterset_class=self.django_filterset_class,
            **dl_kwargs,
        )

    async def handle_get_resource_detail(
        self,
        obj_id: str,
        **extra_view_deps,
    ) -> dict:
        dl: BaseDataLayer = await self.get_data_layer(extra_view_deps)

        view_kwargs = {dl.url_id_field: obj_id}
        db_object = await dl.get_object(view_kwargs=view_kwargs, qs=self.query_params)

        return self._build_detail_response(db_object)

    async def handle_get_resource_relationship(
        self,
        obj_id: str,
        relationship_name: str,
        parent_resource_type: str,
        **extra_view_deps,
    ) -> dict:
        dl: BaseDataLayer = await self.get_data_layer(extra_view_deps)
        view_kwargs = {dl.url_id_field: obj_id}
        db_object = await dl.get_object(
            view_kwargs=view_kwargs,
            qs=self.query_params,
            relationship_request_info=RelationshipRequestInfo(
                parent_resource_type=parent_resource_type,
                parent_obj_id=obj_id,
                relationship_name=relationship_name,
            ),
        )
        return self._build_detail_response(db_object)

    async def handle_get_resource_relationship_list(
        self,
        obj_id: str,
        relationship_name: str,
        parent_resource_type: str,
        **extra_view_deps,
    ) -> dict:
        dl: BaseDataLayer = await self.get_data_layer(extra_view_deps)
        count, items_from_db = await dl.get_collection(
            qs=self.query_params,
            relationship_request_info=RelationshipRequestInfo(
                parent_resource_type=parent_resource_type,
                parent_obj_id=obj_id,
                relationship_name=relationship_name,
            ),
        )
        total_pages = self._calculate_total_pages(count)
        return self._build_list_response(items_from_db, count, total_pages)

    async def handle_create_relationship(
        self,
        obj_id: str,
        relationship_name: str,
        parent_resource_type: str,
        json_data: dict,
        **extra_view_deps,
    ) -> dict:
        """POST to a relationship: adds members to a to-many relationship."""
        dl: BaseDataLayer = await self.get_data_layer(extra_view_deps)
        relationship_info = schemas_storage.get_relationship_info(
            resource_type=parent_resource_type,
            operation_type="get",
            field_name=relationship_name,
        )
        if relationship_info is None:
            raise BadRequest(detail=f"Relationship {relationship_name!r} not found for {parent_resource_type!r}")

        view_kwargs = {dl.url_id_field: obj_id}
        await dl.create_relationship(
            json_data=json_data,
            relationship_field=relationship_name,
            related_id_field=relationship_info.id_field_name,
            view_kwargs=view_kwargs,
        )
        return await self.handle_get_resource_detail(obj_id=obj_id)

    async def handle_update_relationship(
        self,
        obj_id: str,
        relationship_name: str,
        parent_resource_type: str,
        json_data: dict,
        **extra_view_deps,
    ) -> dict:
        """PATCH a relationship: full replacement."""
        dl: BaseDataLayer = await self.get_data_layer(extra_view_deps)
        relationship_info = schemas_storage.get_relationship_info(
            resource_type=parent_resource_type,
            operation_type="get",
            field_name=relationship_name,
        )
        if relationship_info is None:
            raise BadRequest(detail=f"Relationship {relationship_name!r} not found for {parent_resource_type!r}")

        view_kwargs = {dl.url_id_field: obj_id}
        await dl.update_relationship(
            json_data=json_data,
            relationship_field=relationship_name,
            related_id_field=relationship_info.id_field_name,
            view_kwargs=view_kwargs,
        )
        return await self.handle_get_resource_detail(obj_id=obj_id)

    async def handle_delete_relationship(
        self,
        obj_id: str,
        relationship_name: str,
        parent_resource_type: str,
        json_data: dict,
        **extra_view_deps,
    ) -> dict:
        """DELETE from a relationship: removes members from a to-many relationship."""
        dl: BaseDataLayer = await self.get_data_layer(extra_view_deps)
        relationship_info = schemas_storage.get_relationship_info(
            resource_type=parent_resource_type,
            operation_type="get",
            field_name=relationship_name,
        )
        if relationship_info is None:
            raise BadRequest(detail=f"Relationship {relationship_name!r} not found for {parent_resource_type!r}")

        view_kwargs = {dl.url_id_field: obj_id}
        await dl.delete_relationship(
            json_data=json_data,
            relationship_field=relationship_name,
            related_id_field=relationship_info.id_field_name,
            view_kwargs=view_kwargs,
        )
        return await self.handle_get_resource_detail(obj_id=obj_id)

    async def handle_update_resource(
        self,
        obj_id: str,
        data_update: BaseJSONAPIItemInSchema,
        **extra_view_deps,
    ) -> dict:
        dl: BaseDataLayer = await self.get_data_layer(extra_view_deps)
        return await self.process_update_object(dl=dl, obj_id=obj_id, data_update=data_update)

    async def process_update_object(
        self,
        dl: BaseDataLayer,
        obj_id: str,
        data_update: BaseJSONAPIItemInSchema,
    ) -> dict:
        if obj_id != data_update.id:
            raise BadRequest(
                detail="obj_id and data.id should be same.",
                pointer="/data/id",
            )
        view_kwargs = {
            dl.url_id_field: obj_id,
        }
        db_object = await dl.get_object(view_kwargs=view_kwargs, qs=self.query_params)

        await dl.update_object(db_object, data_update, view_kwargs)

        return self._build_detail_response(db_object)

    async def handle_delete_resource(
        self,
        obj_id: str,
        **extra_view_deps,
    ) -> None:
        dl: BaseDataLayer = await self.get_data_layer(extra_view_deps)
        await self.process_delete_object(dl=dl, obj_id=obj_id)

    async def process_delete_object(
        self,
        dl: BaseDataLayer,
        obj_id: str,
    ) -> None:
        view_kwargs = {dl.url_id_field: obj_id}
        db_object = await dl.get_object(view_kwargs=view_kwargs, qs=self.query_params)

        await dl.delete_object(db_object, view_kwargs)

    async def handle_get_resource_list(self, **extra_view_deps) -> dict:
        dl: BaseDataLayer = await self.get_data_layer(extra_view_deps)
        count, items_from_db = await dl.get_collection(qs=self.query_params)
        total_pages = self._calculate_total_pages(count)

        return self._build_list_response(items_from_db, count, total_pages)

    async def handle_post_resource_list(
        self,
        data_create: BaseJSONAPIItemInSchema,
        **extra_view_deps,
    ) -> dict:
        dl: BaseDataLayer = await self.get_data_layer(extra_view_deps)
        return await self.process_create_object(dl=dl, data_create=data_create)

    async def process_create_object(self, dl: BaseDataLayer, data_create: BaseJSONAPIItemInSchema) -> dict:
        db_object = await dl.create_object(data_create=data_create, view_kwargs={})

        view_kwargs = {dl.url_id_field: models_storage.get_object_id(db_object, self.resource_type)}
        if self.query_params.include:
            db_object = await dl.get_object(view_kwargs=view_kwargs, qs=self.query_params)

        return self._build_detail_response(db_object)

    async def handle_delete_resource_list(self, **extra_view_deps) -> dict:
        dl: BaseDataLayer = await self.get_data_layer(extra_view_deps)
        count, items_from_db = await dl.get_collection(qs=self.query_params)
        total_pages = self._calculate_total_pages(count)

        await dl.delete_objects(items_from_db, {})

        return self._build_list_response(items_from_db, count, total_pages)

    async def _run_handler(
        self,
        handler: Callable,
        dto: Optional[BaseModel] = None,
    ):
        handler = partial(handler, self, dto) if dto is not None else partial(handler, self)

        if inspect.iscoroutinefunction(handler):
            return await handler()

        return await asyncio.to_thread(handler)

    async def _handle_config(
        self,
        config: OperationConfig,
        extra_view_deps: dict[str, Any],
    ) -> dict[str, Any]:
        if config.handler is None:
            return {}

        if config.dependencies:
            dto_class: Type[PydanticBaseModel] = config.dependencies
            dto = dto_class(**extra_view_deps)
            return await self._run_handler(config.handler, dto)

        return await self._run_handler(config.handler)

    async def handle_endpoint_dependencies(
        self,
        extra_view_deps: dict[str, Any],
    ) -> dict:
        """
        :return dict: this is **kwargs for DataLayer.__init___
        """
        dl_kwargs = {}
        if common_method_config := self.operation_dependencies.get(Operation.ALL):
            dl_kwargs.update(await self._handle_config(common_method_config, extra_view_deps))

        if method_config := self.operation_dependencies.get(self.operation):
            dl_kwargs.update(await self._handle_config(method_config, extra_view_deps))

        return dl_kwargs

    def _calculate_total_pages(self, db_items_count: Optional[int]) -> Optional[int]:
        if db_items_count is None:
            return None

        total_pages = 1
        if not (pagination_size := self.query_params.pagination.size):
            return total_pages

        return db_items_count // pagination_size + (
            # one more page if not a multiple of size
            (db_items_count % pagination_size) and 1
        )

    def _validate_include_paths(self):
        if not schemas_storage.has_resource(self.resource_type):
            return

        for include_path in self.query_params.include:
            resource_type = self.resource_type
            for relationship_name in include_path.split("."):
                info = schemas_storage.get_relationship_info(
                    resource_type=resource_type,
                    operation_type="get",
                    field_name=relationship_name,
                )
                if info is None:
                    raise InvalidInclude(
                        detail=(
                            f"Relationship {relationship_name!r} is not available for resource type {resource_type!r}."
                        )
                    )

                resource_type = info.resource_type

    @staticmethod
    def _normalize_path(path: str) -> str:
        normalized = "/" + path.strip("/")
        return f"{normalized}/"

    def _get_api_prefix(self) -> str:
        if self._api_prefix is not None:
            return self._api_prefix

        resource_path = models_storage.get_resource_path(self.resource_type).rstrip("/")
        path = self.request.path
        idx = path.find(resource_path)
        self._api_prefix = path[:idx] if idx >= 0 else ""
        return self._api_prefix

    def _build_resource_path(self, resource_type: str, resource_id: Optional[str] = None) -> str:
        base = self._normalize_path(models_storage.get_resource_path(resource_type))
        prefix = self._get_api_prefix().rstrip("/")
        if resource_id is None:
            return f"{prefix}{base}"

        return f"{prefix}{base}{resource_id}/"

    def _build_relationship_links(self, resource_type: str, resource_id: str, relationship_name: str) -> dict[str, str]:
        detail_path = self._build_resource_path(resource_type, resource_id)
        return {
            "self": self.request.build_absolute_uri(f"{detail_path}relationships/{relationship_name}/"),
            "related": self.request.build_absolute_uri(f"{detail_path}{relationship_name}/"),
        }

    @staticmethod
    def _replace_query_params(url: str, params: dict[str, Optional[Any]]) -> str:
        split = urlsplit(url)
        query = parse_qs(split.query, keep_blank_values=True)
        for key, value in params.items():
            if value is None:
                query.pop(key, None)
                continue
            query[key] = [str(value)]

        encoded = urlencode(query, doseq=True)
        return urlunsplit((split.scheme, split.netloc, split.path, encoded, split.fragment))

    def _build_pagination_links(self, count: Optional[int], total_pages: Optional[int]) -> dict[str, Optional[str]]:
        self_url = self.request.build_absolute_uri(self.request.get_full_path())
        links: dict[str, Optional[str]] = {
            "self": self_url,
            "first": None,
            "last": None,
            "prev": None,
            "next": None,
        }

        if self.query_params.pagination.cursor and self.query_params.pagination.size:
            page_size = self.query_params.pagination.size
            links["first"] = self._replace_query_params(
                self_url,
                {"page[cursor]": 0, "page[size]": page_size},
            )
            if self.query_params.pagination.next_cursor is not None:
                links["next"] = self._replace_query_params(
                    self_url,
                    {"page[cursor]": self.query_params.pagination.next_cursor, "page[size]": page_size},
                )

            return links

        if self.query_params.pagination.size:
            page_size = self.query_params.pagination.size
            page_number = max(1, self.query_params.pagination.number)
            last_page = max(1, total_pages or 1)

            links["first"] = self._replace_query_params(self_url, {"page[number]": 1, "page[size]": page_size})
            links["last"] = self._replace_query_params(
                self_url,
                {"page[number]": last_page, "page[size]": page_size},
            )

            if page_number > 1:
                links["prev"] = self._replace_query_params(
                    self_url,
                    {"page[number]": page_number - 1, "page[size]": page_size},
                )

            if page_number < last_page:
                links["next"] = self._replace_query_params(
                    self_url,
                    {"page[number]": page_number + 1, "page[size]": page_size},
                )

            return links

        offset = self.query_params.pagination.offset
        limit = self.query_params.pagination.limit
        if count is None or offset is None or limit is None:
            return links

        links["first"] = self._replace_query_params(self_url, {"page[offset]": 0, "page[limit]": limit})
        last_offset = 0 if count == 0 else ((count - 1) // limit) * limit
        links["last"] = self._replace_query_params(
            self_url,
            {"page[offset]": last_offset, "page[limit]": limit},
        )

        if offset > 0:
            links["prev"] = self._replace_query_params(
                self_url,
                {"page[offset]": max(0, offset - limit), "page[limit]": limit},
            )

        if offset + limit < count:
            links["next"] = self._replace_query_params(
                self_url,
                {"page[offset]": offset + limit, "page[limit]": limit},
            )

        return links

    @classmethod
    def _prepare_item_data(
        cls,
        db_item,
        resource_type: str,
        include_fields: Optional[dict[str, dict[str, Type[TypeSchema]]]] = None,
    ) -> dict:
        object_id = f"{models_storage.get_object_id(db_item, resource_type)}"
        attrs_schema = schemas_storage.get_attrs_schema(resource_type, operation_type="get")
        meta_fields = schemas_storage.get_meta_fields(resource_type, operation_type="get")
        resource_meta: dict[str, Any] = {}

        for meta_field in meta_fields:
            if hasattr(db_item, meta_field):
                resource_meta[meta_field] = getattr(db_item, meta_field)

        if include_fields is None or not (field_schemas := include_fields.get(resource_type)):
            data_schema = schemas_storage.get_data_schema(resource_type, operation_type="get")
            result = data_schema(
                id=object_id,
                attributes=attrs_schema.model_validate(db_item),
            ).model_dump(by_alias=True)

            for meta_field in meta_fields:
                result.get("attributes", {}).pop(meta_field, None)

            if resource_meta:
                result["meta"] = resource_meta

            result["links"] = {}
            return result

        result_attributes = {}
        # empty str means skip all attributes
        if "" not in field_schemas:
            pre_values = {}
            for field_name in field_schemas:
                pre_values[field_name] = getattr(db_item, field_name)

            before_validators, after_validators = schemas_storage.get_model_validators(
                resource_type,
                operation_type="get",
            )
            if before_validators:
                for validator in before_validators.values():
                    if hasattr(validator.wrapped, "__func__"):
                        pre_values = validator.wrapped.__func__(attrs_schema, pre_values)
                        continue

                    pre_values = validator.wrapped(pre_values)

            for field_name, field_schema in field_schemas.items():
                validated_model = field_schema(**{field_name: pre_values[field_name]})

                if after_validators:
                    for validator in after_validators.values():
                        if hasattr(validator.wrapped, "__func__"):
                            validated_model = validator.wrapped.__func__(attrs_schema, validated_model)
                            continue

                        validated_model = validator.wrapped(validated_model)

                result_attributes[field_name] = getattr(validated_model, field_name)

        attrs = {key: value for key, value in result_attributes.items() if key not in meta_fields}
        inflection = get_inflection_formatter()
        if inflection:
            attrs = format_keys(attrs, inflection)
        result = {
            "id": object_id,
            "type": resource_type,
            "attributes": attrs,
            "links": {},
        }

        if resource_meta:
            result["meta"] = resource_meta

        return result

    def _prepare_include_params(self) -> list[list[str]]:
        result = []
        includes = sorted(self.query_params.include)
        prev, *_ = includes

        for include in includes:
            if not include.startswith(prev):
                result.append(prev.split("."))

            prev = include

        result.append(prev.split("."))
        return result

    @classmethod
    def _get_include_key(cls, db_item: TypeModel, info: RelationshipInfo) -> tuple[str, str]:
        return info.resource_type, str(getattr(db_item, info.id_field_name))

    def _process_includes(
        self,
        db_items: list[TypeModel],
        items_data: list[dict],
        resource_type: str,
        include_paths: list[Iterable[str]],
        include_fields: dict[str, dict[str, Type[TypeSchema]]],
        result_included: Optional[dict] = None,
    ) -> dict[tuple[str, str], dict]:
        result_included = result_included or {}

        for db_item, item_data in zip(db_items, items_data, strict=False):
            item_data["relationships"] = item_data.get("relationships", {})
            item_data.setdefault("links", {})["self"] = self.request.build_absolute_uri(
                self._build_resource_path(
                    resource_type=resource_type,
                    resource_id=str(models_storage.get_object_id(db_item, resource_type)),
                )
            )

            for path in include_paths:
                target_relationship, *include_path = path
                info: RelationshipInfo = schemas_storage.get_relationship_info(
                    resource_type=resource_type,
                    operation_type="get",
                    field_name=target_relationship,
                )
                if info is None:
                    raise InvalidInclude(
                        detail=(
                            f"Relationship {target_relationship!r} is not available for "
                            f"resource type {resource_type!r}."
                        )
                    )
                relationship_attr_name = info.model_field_name or target_relationship
                db_items_to_process: list[TypeModel] = []
                items_data_to_process: list[dict] = []

                if info.many:
                    relationship_data = []
                    relationship_db_items = getattr(db_item, relationship_attr_name)
                    if hasattr(relationship_db_items, "all") and callable(relationship_db_items.all):
                        relationship_db_items = relationship_db_items.all()

                    for relationship_db_item in relationship_db_items:
                        include_key = self._get_include_key(relationship_db_item, info)

                        if not (relationship_item_data := result_included.get(include_key)):
                            relationship_item_data = self._prepare_item_data(
                                db_item=relationship_db_item,
                                resource_type=info.resource_type,
                                include_fields=include_fields,
                            )
                            result_included[include_key] = relationship_item_data

                        db_items_to_process.append(relationship_db_item)
                        relationship_data.append(
                            {
                                "id": str(getattr(relationship_db_item, info.id_field_name)),
                                "type": info.resource_type,
                            },
                        )
                        items_data_to_process.append(relationship_item_data)
                else:
                    if (relationship_db_item := getattr(db_item, relationship_attr_name)) is None:
                        item_data["relationships"][target_relationship] = {"data": None}
                        continue

                    db_items_to_process.append(relationship_db_item)
                    relationship_data = {
                        "id": str(getattr(relationship_db_item, info.id_field_name)),
                        "type": info.resource_type,
                    }

                    include_key = self._get_include_key(relationship_db_item, info)

                    if not (relationship_item_data := result_included.get(include_key)):
                        relationship_item_data = self._prepare_item_data(relationship_db_item, info.resource_type)
                        result_included[include_key] = relationship_item_data

                    items_data_to_process.append(relationship_item_data)

                if include_path:
                    self._process_includes(
                        db_items=db_items_to_process,
                        items_data=items_data_to_process,
                        resource_type=info.resource_type,
                        include_paths=[include_path],
                        result_included=result_included,
                        include_fields=include_fields,
                    )

                item_data["relationships"][target_relationship] = {
                    "data": relationship_data,
                    "links": self._build_relationship_links(
                        resource_type=resource_type,
                        resource_id=str(models_storage.get_object_id(db_item, resource_type)),
                        relationship_name=target_relationship,
                    ),
                }

        return result_included

    @classmethod
    def _get_schema_field_names(cls, schema: type[TypeSchema]) -> set[str]:
        """Returns all attribute names except relationships"""
        result = set()

        for field_name, field in schema.model_fields.items():
            if get_relationship_info_from_field_metadata(field):
                continue

            result.add(field_name)

        return result

    def _get_include_fields(self) -> dict[str, dict[str, Type[TypeSchema]]]:
        include_fields = {}
        for resource_type, field_names in self.query_params.fields.items():
            include_fields[resource_type] = {}

            for field_name in field_names:
                include_fields[resource_type][field_name] = schemas_storage.get_field_schema(
                    resource_type=resource_type,
                    operation_type="get",
                    field_name=field_name,
                )

        return include_fields

    def _build_detail_response(self, db_item: TypeModel) -> dict:
        include_fields = self._get_include_fields()
        item_data = self._prepare_item_data(db_item, self.resource_type, include_fields)
        item_data.setdefault("links", {})["self"] = self.request.build_absolute_uri(
            self._build_resource_path(
                resource_type=self.resource_type,
                resource_id=str(models_storage.get_object_id(db_item, self.resource_type)),
            )
        )
        response = {
            "data": item_data,
            "meta": None,
            "links": {"self": self.request.build_absolute_uri(self.request.get_full_path())},
        }
        if self.include_jsonapi_object:
            response["jsonapi"] = {"version": self.jsonapi_version}

        if self.query_params.include:
            included = self._process_includes(
                db_items=[db_item],
                items_data=[item_data],
                include_paths=self._prepare_include_params(),
                resource_type=self.resource_type,
                include_fields=include_fields,
            )
            response["included"] = [value for _, value in sorted(included.items(), key=lambda item: item[0])]

        return response

    def _build_list_response(
        self,
        items_from_db: list[TypeModel],
        count: Optional[int],
        total_pages: Optional[int],
    ) -> dict:
        include_fields = self._get_include_fields()
        items_data = [self._prepare_item_data(db_item, self.resource_type, include_fields) for db_item in items_from_db]
        for db_item, item_data in zip(items_from_db, items_data, strict=False):
            item_data.setdefault("links", {})["self"] = self.request.build_absolute_uri(
                self._build_resource_path(
                    resource_type=self.resource_type,
                    resource_id=str(models_storage.get_object_id(db_item, self.resource_type)),
                )
            )
        response = {
            "data": items_data,
            "meta": {"count": count, "totalPages": total_pages},
            "links": self._build_pagination_links(count=count, total_pages=total_pages),
        }
        if self.include_jsonapi_object:
            response["jsonapi"] = {"version": self.jsonapi_version}

        if self.query_params.include:
            included = self._process_includes(
                db_items=items_from_db,
                items_data=items_data,
                resource_type=self.resource_type,
                include_paths=self._prepare_include_params(),
                include_fields=include_fields,
            )
            response["included"] = [value for _, value in sorted(included.items(), key=lambda item: item[0])]

        return response
