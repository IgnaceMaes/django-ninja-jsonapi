# Configuration

`QueryStringManager` reads settings from Django `NINJA_JSONAPI`.

## Settings

```python
NINJA_JSONAPI = {
    "DEFAULT_PAGE_SIZE": 20,
    "MAX_PAGE_SIZE": 100,
    "MAX_INCLUDE_DEPTH": 3,
    "ALLOW_DISABLE_PAGINATION": False,
    "INCLUDE_JSONAPI_OBJECT": False,
    "JSONAPI_VERSION": "1.0",
}
```

## Keys

- `DEFAULT_PAGE_SIZE`: default number of items per page when the client
  doesn't send `page[size]`.
- `MAX_PAGE_SIZE`: hard upper limit for `page[size]`.  Client-requested sizes
  above this value are clamped silently.
- `MAX_INCLUDE_DEPTH`: maximum include chain depth (for example `a.b.c`).
- `ALLOW_DISABLE_PAGINATION`: allows/disallows `page[size]=0`.
    - When `True`, `page[size]=0` disables pagination.
    - When `False`, `page[size]=0` falls back to the default page size.
- `INCLUDE_JSONAPI_OBJECT`: when `True`, adds top-level `jsonapi` object to
  responses.
- `JSONAPI_VERSION`: version string used when `INCLUDE_JSONAPI_OBJECT=True`.
- `INFLECTION`: attribute-key transformation applied to JSON:API documents.
    - `None` (default) — keys match Python field names.
    - `"dasherize"` — `first_name` → `first-name`.
    - `"camelize"` — `first_name` → `firstName`.
    - See [Inflection](inflection.md) for details.

## Practical guidance

- Keep `MAX_INCLUDE_DEPTH` conservative to avoid expensive graph traversal.
- Set `MAX_PAGE_SIZE` based on endpoint cost and typical client use.

## Query parameters supported

- `filter`
- `filter[field]=value`
- `sort`
- `include`
- `fields[resource_type]`
- `page[number]`, `page[size]`, `page[offset]`, `page[limit]`
- `page[cursor]` (cursor pagination)

## Query parameter validation

- Unknown query parameters are rejected with `400 Bad Request`.
- Repeated parameters are rejected for non-`filter` keys (for example repeating `sort` or `page[size]`).
- Repeating `filter[...]` keys is allowed.

## Resource meta fields

To move selected schema fields into resource `meta`, define `meta_fields`:

```python
class CustomerSchema(BaseModel):
    id: int
    name: str
    status: str

    class JSONAPIMeta:
        meta_fields = ["status"]
```
