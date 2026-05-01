"""Resource descriptor that bundles JSON:API configuration for a resource type.

Eliminates repetition of ``resource_type``, ``id_field``, ``relationships``,
and schemas across ``jsonapi_body()``, ``jsonapi_response()``, and
``@jsonapi_resource()`` calls.

Example::

    from django_ninja_jsonapi import JsonApiResource

    ArticleResource = JsonApiResource(
        resource_type="articles",
        id_field="uuid",
        schema=ArticleSchema,
        schema_create=ArticleCreateSchema,
        schema_update=ArticleUpdateSchema,
        relationships={
            "author": {"resource_type": "people"},
            "tags": {"resource_type": "tags", "many": True},
        },
    )

    # Then use:
    @api.get("/articles", response=ArticleResource.response(many=True))
    @ArticleResource.decorator()
    def list_articles(request): ...

    @api.post("/articles", response=ArticleResource.response())
    @ArticleResource.decorator()
    def create_article(request, body: ArticleResource.body_create()): ...
"""

from __future__ import annotations

from typing import Any, Callable, Type

from pydantic import BaseModel


class JsonApiResource:
    """Bundles JSON:API configuration for a single resource type.

    Parameters are the same as those spread across ``jsonapi_response()``,
    ``jsonapi_body()``, and ``@jsonapi_resource()`` — but defined once.
    """

    def __init__(
        self,
        resource_type: str,
        *,
        id_field: str = "id",
        schema: Type[BaseModel] | None = None,
        schema_create: Type[BaseModel] | None = None,
        schema_update: Type[BaseModel] | None = None,
        relationships: dict[str, Any] | None = None,
        include_jsonapi_object: object | None = None,
        jsonapi_version: str | None = None,
    ) -> None:
        self.resource_type = resource_type
        self.id_field = id_field
        self._schema = schema
        self._schema_create = schema_create
        self._schema_update = schema_update
        self.relationships = relationships
        self._include_jsonapi_object = include_jsonapi_object
        self._jsonapi_version = jsonapi_version

    # ----- Response schemas -----

    def response(self, *, many: bool = False) -> Type[BaseModel]:
        """Build a ``jsonapi_response()`` schema.

        Args:
            many: ``True`` for collection responses.

        Returns:
            A Pydantic model suitable for ``response=`` in a Django Ninja endpoint.
        """
        from django_ninja_jsonapi.schema_factory import jsonapi_response

        if self._schema is None:
            msg = "JsonApiResource.response() requires 'schema' to be set"
            raise ValueError(msg)

        return jsonapi_response(
            self._schema,
            self.resource_type,
            many=many,
            relationships=self.relationships,
        )

    # ----- Body schemas -----

    def body(
        self,
        *,
        schema: Type[BaseModel] | None = None,
        allow_id: bool = False,
    ) -> Type[BaseModel]:
        """Build a ``jsonapi_body()`` schema.

        Args:
            schema: Override the schema to use (defaults to ``schema_create``
                then ``schema``).
            allow_id: Whether to accept a client-generated ``id``.

        Returns:
            A Pydantic model suitable for body type-annotation.
        """
        from django_ninja_jsonapi.schema_factory import jsonapi_body

        effective = schema or self._schema_create or self._schema
        if effective is None:
            msg = "JsonApiResource.body() requires 'schema', 'schema_create', or 'schema' to be set"
            raise ValueError(msg)

        return jsonapi_body(
            effective,
            self.resource_type,
            relationships=self.relationships,
            allow_id=allow_id,
        )

    def body_create(self, *, allow_id: bool = False) -> Type[BaseModel]:
        """Shortcut for ``body()`` using ``schema_create`` (falls back to ``schema``)."""
        return self.body(schema=self._schema_create, allow_id=allow_id)

    def body_update(self, *, allow_id: bool = False) -> Type[BaseModel]:
        """Shortcut for ``body()`` using ``schema_update`` (falls back to ``schema``)."""
        effective = self._schema_update or self._schema
        return self.body(schema=effective, allow_id=allow_id)

    # ----- Decorator -----

    def decorator(self, **overrides: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Build a ``@jsonapi_resource()`` decorator with this resource's config.

        Args:
            **overrides: Any keyword arguments to override on the decorator
                (e.g. ``include_jsonapi_object=True``).

        Returns:
            A decorator function.
        """
        from django_ninja_jsonapi.decorators import jsonapi_resource

        kwargs: dict[str, Any] = {
            "id_field": self.id_field,
            "relationships": self.relationships,
            "schema": self._schema,
        }

        if self._include_jsonapi_object is not None:
            kwargs["include_jsonapi_object"] = self._include_jsonapi_object
        if self._jsonapi_version is not None:
            kwargs["jsonapi_version"] = self._jsonapi_version

        kwargs.update(overrides)

        return jsonapi_resource(self.resource_type, **kwargs)
