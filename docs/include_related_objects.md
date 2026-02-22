# Include related objects

Use `include` to request related resources in the response `included` section.

## Basic include

```http
GET /users/1?include=computers
```

## Nested include

```http
GET /users/1?include=computers.owner
```

## Notes

- `include` works on endpoints that return resource data.
- Maximum depth is controlled by configuration (`MAX_INCLUDE_DEPTH`).
