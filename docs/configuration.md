# Configuration

`QueryStringManager` reads settings from Django `NINJA_JSONAPI`.

## Settings

```python
NINJA_JSONAPI = {
    "MAX_PAGE_SIZE": 100,
    "MAX_INCLUDE_DEPTH": 3,
    "ALLOW_DISABLE_PAGINATION": True,
}
```

## Keys

- `MAX_PAGE_SIZE`: hard upper limit for `page[size]`.
- `MAX_INCLUDE_DEPTH`: maximum include chain depth (for example `a.b.c`).
- `ALLOW_DISABLE_PAGINATION`: allows/disallows `page[size]=0`.

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

## Query parameter validation

- Unknown query parameters are rejected with `400 Bad Request`.
- Repeated parameters are rejected for non-`filter` keys (for example repeating `sort` or `page[size]`).
- Repeating `filter[...]` keys is allowed.
