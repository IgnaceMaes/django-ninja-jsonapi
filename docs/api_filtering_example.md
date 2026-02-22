# API filtering example

This page shows query patterns supported by `QueryStringManager` and consumed by the Django ORM data layer.

## Full filter syntax

```http
GET /users?filter=[{"name":"name","op":"eq","val":"John"}]
```

## Simple filter syntax

```http
GET /users?filter[name]=John
GET /users?filter[name]=John&filter[is_active]=true
```

## Relationship-style field path

```http
GET /users?filter[group.id]=1
```

## Notes

- Keep `filter` URL-encoded in real clients.
- Supported operators depend on your data-layer mapping.
