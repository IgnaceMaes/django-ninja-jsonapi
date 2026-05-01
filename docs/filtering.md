# Filtering

Filtering uses the `filter` query parameter with bracket notation. Use `jsonapi_filter(request, queryset)` to apply filters to a Django queryset.

## Simple filters

```http
GET /customers?filter[name]=John
GET /customers?filter[name]=John&filter[status]=active
```

Simple filters are treated as equality comparisons.

## Relationship-path filters

Dot-separated paths are translated to Django ORM lookups:

```http
GET /customers?filter[computers.serial]=ABC-123
GET /computers?filter[owner.id]=1
```

`filter[computers.serial]=ABC-123` becomes `.filter(computers__serial="ABC-123")` on the queryset.

## Usage with `jsonapi_filter()`

```python
from django_ninja_jsonapi import jsonapi_filter, jsonapi_paginate

@api.get("/customers", response=list[CustomerSchema])
def list_customers(request):
    qs = Customer.objects.all()
    qs = jsonapi_filter(request, qs, allowed_fields={"name", "status"})
    return jsonapi_paginate(request, qs)
```

### `allowed_fields`

Restrict which fields can be filtered on. Fields not in the set are silently ignored.

### `field_map`

Map JSON:API filter names to ORM field expressions:

```python
qs = jsonapi_filter(
    request, qs,
    allowed_fields={"status", "appointment_date"},
    field_map={"appointment_date": "appointment_dt__date"},
)
```

This lets clients use `?filter[appointment_date]=2024-01-01` while the query targets `appointment_dt__date`.

## `QueryStringManager` filter parsing

`QueryStringManager` also parses the full JSON filter format (`?filter=[...]`) with operators and logical combinations. This is a lower-level API for custom filter implementations — `jsonapi_filter()` does not use this format.

## Notes

- URL-encode filter values in production clients.

