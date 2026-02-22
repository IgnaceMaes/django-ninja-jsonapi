# Configuration

`QueryStringManager` reads JSON:API settings from Django settings under `JSONAPI`.

## Settings

```python
JSONAPI = {
    "MAX_INCLUDE_DEPTH": 3,
    "MAX_PAGE_SIZE": 100,
    "ALLOW_DISABLE_PAGINATION": True,
}
```

## Meaning

- `MAX_INCLUDE_DEPTH`: max allowed nesting for `include` paths.
- `MAX_PAGE_SIZE`: cap for `page[size]`.
- `ALLOW_DISABLE_PAGINATION`: allows `page[size]=0` semantics.

## Query parameters supported

- `filter`
- `filter[field]=value`
- `sort`
- `include`
- `fields[resource_type]`
- `page[number]`, `page[size]`, `page[offset]`, `page[limit]`
