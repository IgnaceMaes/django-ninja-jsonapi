"""Transparent JSON:API layer for Django Ninja.

Provides :class:`NinjaJsonAPI`, a drop-in :class:`~ninja.NinjaAPI` subclass
that automatically wraps responses in JSON:API document format and unwraps
incoming JSON:API bodies, so that view functions look exactly like plain
Django Ninja views.

Example::

    from django_ninja_jsonapi import NinjaJsonAPI

    api = NinjaJsonAPI()

    @api.get("/articles", response=list[ArticleSchema])
    def list_articles(request):
        return Article.objects.all()

    @api.post("/articles", response={201: ArticleSchema})
    def create_article(request, body: ArticleCreateSchema):
        return 201, Article.objects.create(**body.dict())
"""

from __future__ import annotations

import inspect
import typing
from functools import wraps
from typing import Any, Callable, Optional, Sequence, Type, Union

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpRequest
from ninja import NinjaAPI, Router
from ninja.constants import NOT_SET, NOT_SET_TYPE
from pydantic import BaseModel

from django_ninja_jsonapi.exceptions import HTTPException
from django_ninja_jsonapi.exceptions.handlers import base_exception_handler, object_does_not_exist_handler
from django_ninja_jsonapi.meta import JsonApiMeta, detect_relationships, get_jsonapi_meta, get_or_default_meta
from django_ninja_jsonapi.renderers import (
    REQUEST_JSONAPI_CONFIG_ATTR,
    JSONAPIRelationshipConfig,
    JSONAPIRenderer,
    JSONAPIResourceConfig,
    normalize_relationships,
)
from django_ninja_jsonapi.schema_factory import JsonApiBody, jsonapi_body, jsonapi_response

# ---------------------------------------------------------------------------
# Request attributes for stashed relationship data
# ---------------------------------------------------------------------------

REQUEST_JSONAPI_BODY_RELATIONSHIPS_ATTR = "_jsonapi_body_relationships"


# ---------------------------------------------------------------------------
# Request-level relationship helpers
# ---------------------------------------------------------------------------


def get_rel_id(request: HttpRequest, name: str) -> str | None:
    """Get the ID of a to-one relationship from the unwrapped JSON:API body.

    Relationship data is stashed on the request during transparent body
    unwrapping performed by :class:`NinjaJsonAPI`.

    Args:
        request: The Django request object.
        name: The relationship name (e.g. ``"author"``).

    Returns:
        The related resource ID as a string, or ``None``.
    """
    rels = getattr(request, REQUEST_JSONAPI_BODY_RELATIONSHIPS_ATTR, None)
    if rels is None:
        return None
    rel = getattr(rels, name, None)
    if rel is None or rel.data is None:
        return None
    return rel.data.id


def get_rel_ids(request: HttpRequest, name: str) -> list[str]:
    """Get the IDs of a to-many relationship from the unwrapped JSON:API body.

    Args:
        request: The Django request object.
        name: The relationship name (e.g. ``"tags"``).

    Returns:
        A list of related resource IDs as strings, or an empty list.
    """
    rels = getattr(request, REQUEST_JSONAPI_BODY_RELATIONSHIPS_ATTR, None)
    if rels is None:
        return []
    rel = getattr(rels, name, None)
    if rel is None or rel.data is None:
        return []
    return [item.id for item in rel.data]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _has_jsonapi_meta(annotation: Any) -> bool:
    """Return True if *annotation* is a BaseModel with ``jsonapi_meta``."""
    try:
        return (
            isinstance(annotation, type)
            and issubclass(annotation, BaseModel)
            and not issubclass(annotation, JsonApiBody)
            and hasattr(annotation, "jsonapi_meta")
            and isinstance(annotation.jsonapi_meta, JsonApiMeta)
        )
    except TypeError:
        return False


def _is_plain_pydantic(annotation: Any) -> bool:
    """Return True if *annotation* is a plain BaseModel (not JsonApiBody)."""
    try:
        return isinstance(annotation, type) and issubclass(annotation, BaseModel) and not issubclass(annotation, JsonApiBody)
    except TypeError:
        return False


def _unwrap_list_type(annotation: Any) -> tuple[bool, Any]:
    """If *annotation* is ``list[X]``, return ``(True, X)``."""
    origin = getattr(annotation, "__origin__", None)
    if origin is list:
        args = typing.get_args(annotation)
        return (True, args[0]) if args else (False, annotation)
    return False, annotation


def _resolve_resource_config(
    schema: Type[BaseModel],
    *,
    relationships: dict[str, JSONAPIRelationshipConfig] | None = None,
) -> JSONAPIResourceConfig:
    """Build a JSONAPIResourceConfig from a schema's JsonApiMeta."""
    from django.conf import settings

    meta = get_or_default_meta(schema)
    resource_type = meta.resolve_resource_type(schema)
    id_field = meta.resolve_id_field(schema)

    if relationships is None:
        relationships = detect_relationships(schema)

    ninja_jsonapi = getattr(settings, "NINJA_JSONAPI", {})
    include_jsonapi = ninja_jsonapi.get("INCLUDE_JSONAPI_OBJECT", False)
    jsonapi_version = ninja_jsonapi.get("JSONAPI_VERSION", "1.0")

    return JSONAPIResourceConfig(
        resource_type=resource_type,
        id_field=id_field,
        include_jsonapi_object=bool(include_jsonapi),
        jsonapi_version=str(jsonapi_version),
        relationships=relationships,
        schema=schema,
    )


def _transform_response(
    response: Any,
) -> tuple[Any, Type[BaseModel] | None]:
    """Transform a ``response=`` parameter to use ``jsonapi_response()``.

    Returns ``(transformed_response, primary_schema)`` where
    *primary_schema* is the first JSON:API-aware schema found (used for
    inferring body resource types), or ``None``.
    """
    if response is NOT_SET or response is None:
        return response, None

    # response=SomeSchema
    if isinstance(response, type) and issubclass(response, BaseModel):
        return _wrap_single_schema(response, many=False)

    # response=list[SomeSchema]
    is_list, inner = _unwrap_list_type(response)
    if is_list and isinstance(inner, type) and issubclass(inner, BaseModel):
        return _wrap_single_schema(inner, many=True)

    # response={200: SomeSchema, 201: SomeSchema, ...}
    if isinstance(response, dict):
        transformed: dict[Any, Any] = {}
        primary: Type[BaseModel] | None = None
        for status_code, schema in response.items():
            if schema is None:
                transformed[status_code] = None
                continue
            # Check for list[Schema]
            is_list, inner = _unwrap_list_type(schema)
            if is_list and isinstance(inner, type) and issubclass(inner, BaseModel):
                wrapped, found = _wrap_single_schema(inner, many=True)
                transformed[status_code] = wrapped
                if found and primary is None:
                    primary = found
            elif isinstance(schema, type) and issubclass(schema, BaseModel):
                wrapped, found = _wrap_single_schema(schema, many=False)
                transformed[status_code] = wrapped
                if found and primary is None:
                    primary = found
            else:
                transformed[status_code] = schema
        return transformed, primary

    return response, None


def _wrap_single_schema(
    schema: Type[BaseModel],
    *,
    many: bool,
) -> tuple[Any, Type[BaseModel] | None]:
    """Wrap a single schema in ``jsonapi_response()`` if it has jsonapi_meta."""
    meta = get_jsonapi_meta(schema)
    if meta is None:
        # No explicit jsonapi_meta — not a JSON:API schema, pass through
        return (list[schema] if many else schema, None)

    resource_type = meta.resolve_resource_type(schema)
    id_field = meta.resolve_id_field(schema)
    relationships = detect_relationships(schema)
    rels = {
        name: {"resource_type": rc.resource_type, "many": rc.many, "id_field": rc.id_field}
        for name, rc in relationships.items()
    }

    wrapped = jsonapi_response(
        schema,
        resource_type,
        many=many,
        relationships=rels or None,
    )
    return wrapped, schema


def _find_body_params(func: Callable[..., Any]) -> dict[str, Type[BaseModel]]:
    """Find function parameters annotated with a plain BaseModel type."""
    hints = typing.get_type_hints(func)
    body_params: dict[str, Type[BaseModel]] = {}
    for name, annotation in hints.items():
        if name == "request" or name == "return":
            continue
        if _is_plain_pydantic(annotation):
            body_params[name] = annotation
    return body_params


def _wrap_view(
    func: Callable[..., Any],
    *,
    response_schema: Type[BaseModel] | None,
    body_params: dict[str, tuple[str, Type[BaseModel], type]],
) -> Callable[..., Any]:
    """Wrap a view function to inject jsonapi_resource config and unwrap body.

    *body_params* maps parameter name → (resource_type, plain_schema, jsonapi_body_type).
    """
    # Build resource config from response schema (or first body schema)
    config_schema = response_schema
    if config_schema is None and body_params:
        _, first_schema, _ = next(iter(body_params.values()))
        config_schema = first_schema

    resource_config = _resolve_resource_config(config_schema) if config_schema is not None else None

    # Build a new signature with JSON:API body types
    new_sig = _build_new_signature(func, body_params)

    if inspect.iscoroutinefunction(func):

        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            request = _extract_request(args=args, kwargs=kwargs)
            if resource_config is not None:
                setattr(request, REQUEST_JSONAPI_CONFIG_ATTR, resource_config)
            _unwrap_body_params(request, kwargs, body_params)
            return await func(*args, **kwargs)

        async_wrapper.__signature__ = new_sig
        return async_wrapper

    @wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        request = _extract_request(args=args, kwargs=kwargs)
        if resource_config is not None:
            setattr(request, REQUEST_JSONAPI_CONFIG_ATTR, resource_config)
        _unwrap_body_params(request, kwargs, body_params)
        return func(*args, **kwargs)

    sync_wrapper.__signature__ = new_sig
    return sync_wrapper


def _unwrap_body_params(
    request: HttpRequest,
    kwargs: dict[str, Any],
    body_params: dict[str, tuple[str, Type[BaseModel], type]],
) -> None:
    """Extract plain schema from JSON:API body and stash relationships on request."""
    for param_name, (_resource_type, _plain_schema, _body_type) in body_params.items():
        if param_name not in kwargs:
            continue
        body = kwargs[param_name]
        if isinstance(body, JsonApiBody):
            # Stash relationship data on request
            rels = getattr(body.data, "relationships", None)
            if rels is not None:
                setattr(request, REQUEST_JSONAPI_BODY_RELATIONSHIPS_ATTR, rels)
            # Replace with plain attributes schema
            kwargs[param_name] = body.data.attributes


def _build_new_signature(
    func: Callable[..., Any],
    body_params: dict[str, tuple[str, Type[BaseModel], type]],
) -> inspect.Signature:
    """Build a new function signature with JSON:API body types replacing plain schema types."""
    sig = inspect.signature(func, follow_wrapped=False)
    if not body_params:
        return sig

    new_params = []
    for name, param in sig.parameters.items():
        if name in body_params:
            _, _, body_type = body_params[name]
            new_params.append(param.replace(annotation=body_type))
        else:
            new_params.append(param)
    return sig.replace(parameters=new_params)


def _extract_request(*, args: tuple[Any, ...], kwargs: dict[str, Any]) -> HttpRequest:
    """Extract the request object from view args/kwargs."""
    request = kwargs.get("request")
    if isinstance(request, HttpRequest):
        return request
    for arg in args:
        if isinstance(arg, HttpRequest):
            return arg
    msg = "NinjaJsonAPI could not locate request argument"
    raise ValueError(msg)


def _build_body_type(
    schema: Type[BaseModel],
    resource_type: str,
    *,
    relationships: dict[str, JSONAPIRelationshipConfig] | None = None,
) -> type:
    """Build a JSON:API body type for a plain schema."""
    rels: dict[str, Any] | None = None
    if relationships:
        rels = {
            name: {"resource_type": rc.resource_type, "many": rc.many, "id_field": rc.id_field}
            for name, rc in relationships.items()
        }
    return jsonapi_body(schema, resource_type, relationships=rels)


# ---------------------------------------------------------------------------
# JsonApiRouter — Router subclass that intercepts add_api_operation
# ---------------------------------------------------------------------------


class JsonApiRouter(Router):
    """A :class:`~ninja.Router` that transparently wraps JSON:API schemas."""

    def add_api_operation(
        self,
        path: str,
        methods: list[str],
        view_func: Callable[..., Any],
        *,
        response: Any = NOT_SET,
        **kwargs: Any,
    ) -> None:
        # --- Transform response= parameter ---
        transformed_response, primary_schema = _transform_response(response)

        # --- Find and transform body parameters ---
        body_params_raw = _find_body_params(view_func)
        body_params: dict[str, tuple[str, Type[BaseModel], type]] = {}

        # Pre-compute response schema relationships for inheritance
        response_rels: dict[str, JSONAPIRelationshipConfig] = {}
        if primary_schema is not None:
            response_rels = detect_relationships(primary_schema)

        for param_name, param_schema in body_params_raw.items():
            # Determine resource type for this body param
            param_meta = get_jsonapi_meta(param_schema)
            if param_meta is not None:
                rt = param_meta.resolve_resource_type(param_schema)
            elif primary_schema is not None:
                pm = get_or_default_meta(primary_schema)
                rt = pm.resolve_resource_type(primary_schema)
            else:
                dm = get_or_default_meta(param_schema)
                rt = dm.resolve_resource_type(param_schema)

            # Detect relationships from the body schema itself, then merge
            # any additional relationships from the response schema
            rels = detect_relationships(param_schema)
            for rel_name, rel_config in response_rels.items():
                if rel_name not in rels:
                    rels[rel_name] = rel_config

            body_type = _build_body_type(param_schema, rt, relationships=rels or None)
            body_params[param_name] = (rt, param_schema, body_type)

        # --- Wrap view function if needed ---
        if body_params or primary_schema is not None:
            view_func = _wrap_view(
                view_func,
                response_schema=primary_schema,
                body_params=body_params,
            )

        super().add_api_operation(
            path,
            methods,
            view_func,
            response=transformed_response,
            **kwargs,
        )


# ---------------------------------------------------------------------------
# NinjaJsonAPI — NinjaAPI subclass
# ---------------------------------------------------------------------------


class NinjaJsonAPI(NinjaAPI):
    """A :class:`~ninja.NinjaAPI` that speaks JSON:API transparently.

    Drop-in replacement for :class:`NinjaAPI` that automatically:

    - Sets the JSON:API renderer and exception handlers
    - Wraps ``response=`` schemas in JSON:API document structure for OpenAPI docs
    - Unwraps incoming JSON:API request bodies so views receive plain schemas
    - Injects ``@jsonapi_resource()`` config on every request

    Usage::

        from django_ninja_jsonapi import NinjaJsonAPI

        api = NinjaJsonAPI()

        @api.get("/articles", response=list[ArticleSchema])
        def list_articles(request):
            return Article.objects.all()
    """

    def __init__(self, **kwargs: Any) -> None:
        # Use JsonApiRouter unless the user provides a custom router
        if "default_router" not in kwargs:
            kwargs["default_router"] = JsonApiRouter()

        # Use JSONAPIRenderer unless the user provides a custom renderer
        if "renderer" not in kwargs:
            kwargs["renderer"] = JSONAPIRenderer()

        super().__init__(**kwargs)

        # Register JSON:API exception handlers
        self.add_exception_handler(HTTPException, base_exception_handler)  # type: ignore[arg-type]
        self.add_exception_handler(ObjectDoesNotExist, object_does_not_exist_handler)  # type: ignore[arg-type]
