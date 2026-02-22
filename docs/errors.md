# Errors

The package exposes JSON:API-friendly exceptions and a shared handler that returns a standardized `errors` envelope.

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

## Recommended usage

Use package exceptions (for example `BadRequest`) in view hooks and data-layer code so errors are consistently serialized.
