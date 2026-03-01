from __future__ import annotations

from typing import Any

from django.db import IntegrityError
from django.db.models import Model, QuerySet

from django_ninja_jsonapi.exceptions import BadRequest, ObjectNotFound


class BaseDjangoORM:
    @staticmethod
    def queryset(model: type[Model]) -> QuerySet:
        return model.objects.all()  # ty: ignore[unresolved-attribute]

    @staticmethod
    def one_or_raise(queryset: QuerySet, **kwargs: Any) -> Model:
        try:
            return queryset.get(**kwargs)
        except queryset.model.DoesNotExist as ex:  # ty: ignore[unresolved-attribute]
            raise ObjectNotFound(detail=f"Resource not found for lookup: {kwargs}") from ex

    @staticmethod
    def create(model: type[Model], **kwargs: Any) -> Model:
        try:
            return model.objects.create(**kwargs)  # ty: ignore[unresolved-attribute]
        except IntegrityError as ex:
            raise BadRequest(detail=str(ex)) from ex

    @staticmethod
    def update(obj: Model, **kwargs: Any) -> Model:
        for key, value in kwargs.items():
            setattr(obj, key, value)

        try:
            obj.save()
        except IntegrityError as ex:
            raise BadRequest(detail=str(ex)) from ex

        return obj

    @staticmethod
    def delete(obj: Model) -> None:
        obj.delete()
