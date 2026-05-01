# Errors

The package exposes JSON:API-friendly exceptions and a shared handler that returns a standardized `errors` envelope.

## Raise package exceptions

```python
from django_ninja_jsonapi.exceptions import BadRequest


@api.post("/articles")
def create_article(request, body: ArticleCreateSchema):
    if not body.title:
        raise BadRequest(detail="Title is required", parameter="data.attributes.title")
    ...
```

## Example (query parameter error)

```json
{
  "errors": [
    {
      "status": "400",
      "source": {"parameter": "include"},
      "title": "Bad Request",
      "detail": "Invalid query parameter: includez"
    }
  ]
}
```

For strict query validation, unknown parameters and repeated non-filter parameters now return `400`.

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

Use package exceptions (for example `BadRequest`) in your views so errors are consistently serialized.
