# Inflection (Attribute Key Transformation)

By default, attribute keys in JSON:API responses match the Python field names on your Pydantic schema (e.g. `first_name`).  You can configure `django-ninja-jsonapi` to automatically transform keys to dasherized or camelCase form.

## Configuration

Add `INFLECTION` to your `NINJA_JSONAPI` settings:

```python
NINJA_JSONAPI = {
    "INFLECTION": "dasherize",  # or "camelize", or None (default)
}
```

| Value         | Python field   | JSON:API key   |
| ------------- | -------------- | -------------- |
| `None`        | `first_name`   | `first_name`   |
| `"dasherize"` | `first_name`   | `first-name`   |
| `"camelize"`  | `first_name`   | `firstName`    |

## How it works

When inflection is enabled:

1. **Outgoing responses** — attribute keys are transformed before serialisation, so `first_name` appears as `first-name` or `firstName` in the JSON document.
2. **Sparse fieldsets** — `fields[customer]=first-name` is accepted and mapped back to the underlying `first_name` field.
3. **Schema aliases** — dynamically built Pydantic models get an `alias_generator` so `model_dump(by_alias=True)` produces transformed keys automatically.

## Example

Schema:

```python
class CustomerSchema(BaseModel):
    id: int
    first_name: str
    last_name: str
```

With `"INFLECTION": "dasherize"`:

```json
{
  "data": {
    "type": "customer",
    "id": "1",
    "attributes": {
      "first-name": "Alice",
      "last-name": "Smith"
    }
  }
}
```

## Manual use

The inflection functions are available for direct use in custom code:

```python
from django_ninja_jsonapi.inflection import dasherize, camelize, underscore

dasherize("first_name")   # "first-name"
camelize("first_name")    # "firstName"
underscore("first-name")  # "first_name"
underscore("firstName")   # "first_name"
```
