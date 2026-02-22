# Configuration

`QueryStringManager` reads settings from Django `NINJA_JSONAPI`.

## Settings

```python
NINJA_JSONAPI = {
    "MAX_PAGE_SIZE": 20,
    "MAX_INCLUDE_DEPTH": 3,
    "ALLOW_DISABLE_PAGINATION": False,
    "INCLUDE_JSONAPI_OBJECT": False,
    "JSONAPI_VERSION": "1.0",
}
```

## Keys

- `MAX_PAGE_SIZE`: hard upper limit for `page[size]`.
- `MAX_INCLUDE_DEPTH`: maximum include chain depth (for example `a.b.c`).
- `ALLOW_DISABLE_PAGINATION`: allows/disallows `page[size]=0`.
    - When `True`, `page[size]=0` disables pagination.
    - When `False`, `page[size]=0` falls back to the default page size.
- `INCLUDE_JSONAPI_OBJECT`: when `True`, adds top-level `jsonapi` object to responses.
- `JSONAPI_VERSION`: version string used when `INCLUDE_JSONAPI_OBJECT=True`.

## Practical guidance

- Keep `MAX_INCLUDE_DEPTH` conservative to avoid expensive graph traversal.
- Set `MAX_PAGE_SIZE` based on endpoint cost and typical client use.
- Use per-resource operation limits when read-heavy resources need stricter controls.

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

## Include-query optimization

The Django ORM data layer now optimizes include paths automatically:

- to-one include chains use `select_related`
- to-many include chains use `prefetch_related`

You can also provide explicit include optimization maps on your view:

```python
from django_ninja_jsonapi import ViewBaseGeneric


class CustomerView(ViewBaseGeneric):
    select_for_includes = {
        "__all__": ["company"],
        "owner": ["owner__profile"],
    }
    prefetch_for_includes = {
        "owner": ["owner__groups"],
    }
    django_filterset_class = CustomerFilterSet
```

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
