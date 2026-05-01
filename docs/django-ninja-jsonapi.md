# django-ninja-jsonapi package

## Public imports

```python
from django_ninja_jsonapi import (
    NinjaJsonAPI,
    JsonApiMeta,
    JSONAPIRenderer,
    QueryStringManager,
    HTTPException,
    BadRequest,
    NotFound,
    apply_attributes,
    get_rel_id,
    get_rel_ids,
    model_schema,
    jsonapi_paginate,
    jsonapi_pagination,
    jsonapi_cursor_pagination,
    jsonapi_include,
    jsonapi_meta,
    jsonapi_links,
    jsonapi_sort,
    jsonapi_filter,
    parse_include,
)
```

## Primary modules

- `transparent` — `NinjaJsonAPI` and `JsonApiRouter` for transparent JSON:API wrapping
- `meta` — `JsonApiMeta` schema-level configuration
- `querystring` — JSON:API query parameter parsing
- `renderers` — `JSONAPIRenderer` for JSON:API response formatting
- `exceptions` — JSON:API error definitions and handler
- `response_helpers` — pagination, include, links, meta, sort, filter helpers
