# Errors

The package exposes JSON:API-friendly exceptions and a shared handler that returns a standardized `errors` envelope.

## Raise package exceptions in custom logic

```python
from django_ninja_jsonapi.exceptions import BadRequest
from django_ninja_jsonapi.views.view_base import ViewBase


class CustomerView(ViewBase):
  async def post_resource_list_result(self, data_create, **extra_view_deps):
    if not data_create.attributes.get("name"):
      raise BadRequest(detail="Name is required", parameter="data.attributes.name")
    return await super().post_resource_list_result(data_create, **extra_view_deps)
```

## Example (query parameter error)

```json
{
  "errors": [
    {
      "status": "400",
      "source": {"parameter": "include"},
      "title": "BadRequest",
      "detail": "Include parameter is invalid"
    }
  ],
  "jsonapi": {"version": "1.0"}
}
```

## Example (resource validation error)

```json
{
  "errors": [
    {
      "status": "422",
      "source": {"pointer": "/data/attributes/name"},
      "title": "Unprocessable Entity",
      "detail": "Name must be at least 3 characters"
    }
  ]
}
```

## Recommended usage

Use package exceptions (for example `BadRequest`) in view hooks and data-layer code so errors are consistently serialized.
