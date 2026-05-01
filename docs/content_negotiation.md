# Content Negotiation

`django-ninja-jsonapi` enforces JSON:API content-type negotiation on endpoints that receive a request body.

## Behaviour

### 415 Unsupported Media Type

A `POST`, `PATCH`, or `DELETE`-with-body request **must** use `Content-Type: application/vnd.api+json`. The `ext` and `profile` media type parameters are permitted per [§6.3](https://jsonapi.org/format/#content-negotiation-servers), but all other parameters are rejected.

The following are rejected:

| Content-Type header                                | Result |
| -------------------------------------------------- | ------ |
| `application/json`                                 | 415    |
| `application/vnd.api+json; charset=utf-8`          | 415    |
| `text/html`                                        | 415    |

The following are accepted:

| Content-Type header                                                    | Result |
| ---------------------------------------------------------------------- | ------ |
| `application/vnd.api+json`                                             | OK     |
| `application/vnd.api+json; ext="https://jsonapi.org/ext/atomic"`       | OK     |
| `application/vnd.api+json; profile="http://example.com/last-modified"` | OK     |

### 406 Not Acceptable

If the `Accept` header contains `application/vnd.api+json` **and every instance** of it includes media type parameters (other than `ext` or `profile`), the server responds with `406 Not Acceptable`.

```
Accept: application/vnd.api+json; version=1
→ 406 Not Acceptable

Accept: application/vnd.api+json; version=1, text/html
→ 200 OK  (text/html acts as a fallback)

Accept: application/vnd.api+json; ext="atomic"
→ 200 OK  (ext is allowed)
```

If the `Accept` header does not mention the JSON:API media type at all (or is absent), the request is allowed through — the server responds with the JSON:API media type regardless.

## Manual validation

You can call the validators directly if needed:

```python
from django_ninja_jsonapi.content_negotiation import validate_accept, validate_content_type

validate_content_type(request)  # raises UnsupportedMediaType (415)
validate_accept(request)        # raises NotAcceptable (406)
```
