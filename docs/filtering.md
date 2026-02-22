# Filtering

Filtering uses the `filter` query parameter and is translated by the data layer.

## Full JSON filter format

```http
GET /users?filter=[{"name":"name","op":"eq","val":"John"}]
```

## Simple filters

```http
GET /users?filter[name]=John
GET /users?filter[name]=John&filter[status]=active
```

Simple filters are treated as `eq` comparisons.

## Logical combinations

You can send full filter objects for complex expressions (`and`, `or`, `not`) when your data layer supports them.

## Notes

- URL-encode JSON values in production clients.
- Supported operators are data-layer specific.
