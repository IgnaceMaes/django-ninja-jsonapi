# API Reference

## Public imports

```python
from django_ninja_jsonapi import (
    NinjaJsonAPI,
    JsonApiMeta,
    ModelSchema,
    JSONAPIRenderer,
    QueryStringManager,
    HTTPException,
    BadRequest,
    NotFound,
    apply_attributes,
    get_rel_id,
    get_rel_ids,
    jsonapi_paginate,
    jsonapi_pagination,
    jsonapi_cursor_pagination,
    jsonapi_include,
    jsonapi_links,
    jsonapi_meta,
    jsonapi_sort,
    jsonapi_filter,
    parse_include,
)
```

## `NinjaJsonAPI`

Location: `django_ninja_jsonapi.transparent.NinjaJsonAPI`

A `NinjaAPI` subclass that automatically wraps responses in JSON:API document format and unwraps JSON:API request bodies into plain Pydantic schemas.

### Constructor

```python
NinjaJsonAPI(**kwargs)
```

Accepts all `NinjaAPI` keyword arguments. Automatically sets the renderer to `JSONAPIRenderer` and registers the JSON:API exception handler.

### Behavior

- Response schemas are automatically wrapped into JSON:API document format with `data`, `id`, `type`, `attributes`, and `relationships`.
- Request body parameters are automatically unwrapped — your endpoint receives plain Pydantic model instances instead of nested JSON:API structures.
- Resource type, relationships, and ID field are derived from `JsonApiMeta` on the schema, or inferred by convention.
- Use `JsonApiRouter` for sub-routers that inherit the same behavior.

## `JsonApiRouter`

Location: `django_ninja_jsonapi.transparent.JsonApiRouter`

A Django Ninja `Router` subclass with the same transparent wrapping/unwrapping behavior as `NinjaJsonAPI`. Use for modular route organization.

```python
from django_ninja_jsonapi.transparent import JsonApiRouter

router = JsonApiRouter(tags=["articles"])

@router.get("/articles", response=list[ArticleSchema])
def list_articles(request):
    return Article.objects.all()

api.add_router("", router)
```

## `JsonApiMeta`

Location: `django_ninja_jsonapi.meta.JsonApiMeta`

Schema-level configuration for JSON:API behavior. Attach as a `ClassVar` on Pydantic schemas.

### Constructor

```python
JsonApiMeta(
    resource_type: str | None = None,
    id_field: str | None = None,
)
```

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `resource_type` | `str \| None` | `None` | JSON:API type name. Auto-derived from class name if omitted (e.g. `ArticleSchema` → `"articles"`). |
| `id_field` | `str \| None` | `None` | Field used as the resource ID. Defaults to `"id"`, or `"uuid"` if the schema has a `uuid` field but no `id` field. |

### Example

```python
from typing import ClassVar
from pydantic import BaseModel
from django_ninja_jsonapi import JsonApiMeta

class ArticleSchema(BaseModel):
    id: int
    title: str
    author: AuthorSchema | None = None

    jsonapi_meta: ClassVar[JsonApiMeta] = JsonApiMeta(
        resource_type="articles",
    )
```

## `get_rel_id(request, name)`

Location: `django_ninja_jsonapi.transparent.get_rel_id`

Extract a to-one relationship ID from the request body.

```python
author_id = get_rel_id(request, "author")  # str | None
```

## `get_rel_ids(request, name)`

Location: `django_ninja_jsonapi.transparent.get_rel_ids`

Extract to-many relationship IDs from the request body.

```python
tag_ids = get_rel_ids(request, "tags")  # list[str]
```

## `apply_attributes(instance, body, ...)`

Location: `django_ninja_jsonapi.helpers.apply_attributes`

Apply attributes from a request body to a Django model instance.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `instance` | Django Model | required | The model instance to update |
| `body` | Pydantic model | required | The parsed request body (plain schema or legacy wrapper) |
| `save` | `bool` | `True` | Call `instance.save()` with `update_fields` |
| `extra_update_fields` | `Sequence[str]` | `()` | Additional fields for `update_fields` |
| `exclude` | `set[str]` | `None` | Attribute names to skip |

### Returns

A `dict` of the attributes that were applied.

## `ModelSchema`

Location: `django_ninja_jsonapi._model_schema.ModelSchema`

Declarative base class for generating schemas from Django models. Define a `Meta` inner class instead of listing fields manually.

```python
from django_ninja_jsonapi import ModelSchema

class CustomerSchema(ModelSchema):
    class Meta:
        model = Customer
        fields = ["id", "name", "email"]
        resource_type = "customers"
```

See [Model schema](model_schema.md) for `Meta` options and full documentation.

## `JSONAPIRenderer`

Location: `django_ninja_jsonapi.renderers.JSONAPIRenderer`

Django Ninja renderer that produces `application/vnd.api+json` responses. Used automatically by `NinjaJsonAPI`.

## `QueryStringManager`

Location: `django_ninja_jsonapi.querystring.QueryStringManager`

Parses JSON:API query parameters (`filter`, `sort`, `include`, `fields`, `page`) from the request.

## Response helpers

### `jsonapi_paginate(request, queryset, ...)`

Paginate a queryset and attach JSON:API pagination links/meta to the request.

### `jsonapi_pagination(request, *, count, page_size, page_number)`

Low-level pagination helper — sets pagination meta and links on the request without slicing. Use when you've already sliced the data yourself.

### `jsonapi_cursor_pagination(request, *, page_size, next_cursor, prev_cursor)`

Cursor-based pagination — sets cursor-style pagination links on the request.

### `jsonapi_include(request, included)`

Attach included resources to the response.

### `jsonapi_links(request, links)`

Attach top-level links to the response.

### `jsonapi_meta(request, meta)`

Attach top-level meta to the response.

### `jsonapi_sort(request, queryset)`

Apply JSON:API `sort` parameter to a queryset.

### `jsonapi_filter(request, queryset)`

Apply JSON:API `filter` parameter to a queryset.

### `parse_include(request)`

Parse the `include` query parameter into a list of include paths.

## Exceptions

### `HTTPException`

Base JSON:API exception with status code and detail.

### `BadRequest`

400 error.

### `NotFound`

404 error.
