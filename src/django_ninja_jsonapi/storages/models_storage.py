import logging
from typing import Any, Type

from django.core.exceptions import FieldDoesNotExist

from django_ninja_jsonapi.data_typing import TypeModel
from django_ninja_jsonapi.exceptions import BadRequest, InternalServerError

log = logging.getLogger(__name__)


class ModelsStorage:
    def __init__(self):
        self._models: dict[str, Type[TypeModel]] = {}
        self._id_field_names: dict[str, str] = {}
        self._resource_paths: dict[str, str] = {}

    def add_model(self, resource_type: str, model: Type[TypeModel], id_field_name: str, resource_path: str):
        self._models[resource_type] = model
        self._id_field_names[resource_type] = id_field_name
        self._resource_paths[resource_type] = resource_path

    def get_model(self, resource_type: str) -> Type[TypeModel]:
        try:
            return self._models[resource_type]
        except KeyError as ex:
            raise InternalServerError(
                detail=f"Not found model for resource_type {resource_type!r}.",
            ) from ex

    def get_model_id_field_name(self, resource_type: str) -> str:
        try:
            return self._id_field_names[resource_type]
        except KeyError as ex:
            raise InternalServerError(
                detail=f"Not found model id field name for resource_type {resource_type!r}.",
            ) from ex

    def get_resource_path(self, resource_type: str) -> str:
        try:
            return self._resource_paths[resource_type]
        except KeyError as ex:
            raise InternalServerError(
                detail=f"Not found resource path for resource_type {resource_type!r}.",
            ) from ex

    def get_object_id_field(self, resource_type: str) -> Any:
        model = self.get_model(resource_type)
        id_field_name = self.get_model_id_field_name(resource_type)

        try:
            return getattr(model, id_field_name)
        except AttributeError as ex:
            raise InternalServerError(
                detail=f"Can't get object id field. The model {model.__name__!r} has no attribute {id_field_name!r}",
            ) from ex

    def get_object_id(self, db_object: TypeModel, resource_type: str) -> Any:
        id_field_name = self.get_model_id_field_name(resource_type)

        try:
            return getattr(db_object, id_field_name)
        except AttributeError as ex:
            model = self.get_model(resource_type)
            raise InternalServerError(
                detail=f"Can't get object id. The model {model.__name__!r} has no attribute {id_field_name!r}.",
            ) from ex

    def search_relationship_model(
        self,
        resource_type: str,
        model: Type[TypeModel],
        field_name: str,
    ) -> Type[TypeModel]:
        try:
            return self._search_relationship_model(resource_type=resource_type, model=model, field_name=field_name)
        except Exception as ex:
            log.error("Relationship search error", exc_info=ex)
            raise InternalServerError(
                detail=f"Relationship search error for resource_type {resource_type!r} by relation {field_name!r}.",
            ) from ex

    @staticmethod
    def _search_relationship_model(
        resource_type: str,
        model: Type[TypeModel],
        field_name: str,
    ) -> Type[TypeModel]:
        try:
            field = model._meta.get_field(field_name)  # ty: ignore[unresolved-attribute]
        except FieldDoesNotExist as ex:
            raise BadRequest(
                detail=f"There is no related model for resource_type {resource_type!r} by relation {field_name!r}.",
            ) from ex

        related_model = getattr(field, "related_model", None)
        if related_model is None:
            raise BadRequest(
                detail=f"There is no related model for resource_type {resource_type!r} by relation {field_name!r}.",
            )

        return related_model


models_storage = ModelsStorage()
