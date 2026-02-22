# django-ninja-jsonapi package

## Public imports

```python
from django_ninja_jsonapi import (
    ApplicationBuilder,
    QueryStringManager,
    ViewBaseGeneric,
    HTTPException,
    BadRequest,
)
```

## Primary modules

- `api` — route and endpoint builders
- `querystring` — JSON:API query parameter parsing
- `data_layers.django_orm` — Django ORM integration
- `exceptions` — JSON:API error definitions and handler
- `atomic` — atomic operations endpoint plumbing
