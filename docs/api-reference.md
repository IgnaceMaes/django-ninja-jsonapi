# API Reference

## Public imports

```python
from django_ninja_jsonapi import ApplicationBuilder, QueryStringManager, HTTPException, BadRequest, ViewBaseGeneric
```

## `ApplicationBuilder`

Location: `django_ninja_jsonapi.api.application_builder.ApplicationBuilder`

### Constructor

```python
ApplicationBuilder(
    api: NinjaAPI,
    base_router: Router | None = None,
    exception_handler: Callable | None = None,
    **base_router_include_kwargs,
)
```

### `add_resource(...)`

Registers one JSON:API resource.

Parameters:

- `path: str`
- `tags: Iterable[str]`
- `resource_type: str`
- `view: type`
- `model: type`
- `schema: type[BaseModel]`
- `router: Router | None = None`
- `schema_in_post: type[BaseModel] | None = None`
- `schema_in_patch: type[BaseModel] | None = None`
- `pagination_default_size: int | None = 25`
- `pagination_default_number: int | None = 1`
- `pagination_default_offset: int | None = None`
- `pagination_default_limit: int | None = None`
- `operations: Iterable[Operation] = ()`
- `ending_slash: bool = True`
- `model_id_field_name: str = "id"`
- `include_router_kwargs: dict | None = None`

### `initialize()`

Builds and registers routes on the `NinjaAPI` instance.

Generated endpoints include:

- resource list/detail CRUD endpoints
- relationship list/detail GET endpoints (when relationship metadata is available)
- atomic endpoint: `POST /operations`

### Response shape notes

- List/detail responses include top-level `links`.
- Resource objects include `links.self`.
- Relationship objects include `links.self` and `links.related`.

### Django ORM optimizations

- Include paths are split automatically between `select_related` (to-one chains) and `prefetch_related` (to-many chains).
- Filter parsing supports logical trees (`and`, `or`, `not`) in JSON `filter` payloads.
- Cursor pagination is available via `page[cursor]` + `page[size]`.

### Query parameter validation

- Allowed top-level query params: `filter`, `sort`, `include`, `fields[...]`, `page[...]`.
- Unknown params return `400`.
- Repeating non-filter params returns `400`.

## `Operation` enum

Location: `django_ninja_jsonapi.views.enums.Operation`

Values:

- `ALL`
- `CREATE`
- `DELETE`
- `DELETE_LIST`
- `GET`
- `GET_LIST`
- `UPDATE`

Use `Operation.ALL` to auto-expand to all concrete operations.
