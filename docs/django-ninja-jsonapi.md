# django-ninja-jsonapi package

## Public imports

```python
from django_ninja_jsonapi import (
    NinjaJsonAPI,
    JsonApiMeta,
    QueryStringManager,
    HTTPException,
    BadRequest,
)
```

## Primary modules

- `transparent` — `NinjaJsonAPI` and `JsonApiRouter` for transparent JSON:API wrapping
- `meta` — `JsonApiMeta` schema-level configuration
- `querystring` — JSON:API query parameter parsing
- `renderers` — `JSONAPIRenderer` for JSON:API response formatting
- `exceptions` — JSON:API error definitions and handler
- `response_helpers` — pagination, include, links, meta, sort, filter helpers
