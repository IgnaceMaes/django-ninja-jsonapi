# Content Negotiation

`django-ninja-jsonapi` enforces JSON:API content-type negotiation automatically on every `ApplicationBuilder` endpoint that receives a request body.

## Behaviour

### 415 Unsupported Media Type

A `POST`, `PATCH`, or `DELETE`-with-body request **must** use `Content-Type: application/vnd.api+json` without extra media type parameters.

The following are rejected:

| Content-Type header                                | Result |
| -------------------------------------------------- | ------ |
| `application/json`                                 | 415    |
| `application/vnd.api+json; charset=utf-8`          | 415    |
| `text/html`                                        | 415    |

The following is accepted:

| Content-Type header            | Result |
| ------------------------------ | ------ |
| `application/vnd.api+json`     | OK     |

### 406 Not Acceptable

If the `Accept` header contains `application/vnd.api+json` **and every instance** of it includes media type parameters, the server responds with `406 Not Acceptable`.

```
Accept: application/vnd.api+json; version=1
→ 406 Not Acceptable

Accept: application/vnd.api+json; version=1, text/html
→ 200 OK  (text/html acts as a fallback)
```

If the `Accept` header does not mention the JSON:API media type at all (or is absent), the request is allowed through — the server responds with the JSON:API media type regardless.

## No configuration needed

Content negotiation is enabled by default for all `ApplicationBuilder` endpoints.  There is no setting to disable it.

If you use the standalone `@jsonapi_resource` decorator mode, you can call the validators manually:

```python
from django_ninja_jsonapi.content_negotiation import validate_accept, validate_content_type

validate_content_type(request)  # raises UnsupportedMediaType (415)
validate_accept(request)        # raises NotAcceptable (406)
```
