# Filtering

Filtering uses the `filter` query parameter and is translated by the data layer.

## Full JSON filter format (single condition)

```http
GET /customers?filter=[{"name":"name","op":"eq","val":"John"}]
```

```python
import json
from urllib.parse import quote

import httpx

flt = json.dumps([{"name": "name", "op": "eq", "val": "John"}])
url = f"http://localhost:8000/api/customers?filter={quote(flt)}"

response = httpx.get(url)
print(response.status_code, response.json())
```

## Full JSON filter format (multiple conditions)

```http
GET /customers?filter=[{"name":"status","op":"eq","val":"active"},{"name":"age","op":"ge","val":18}]
```

## Simple filters

```http
GET /customers?filter[name]=John
GET /customers?filter[name]=John&filter[status]=active
```

Simple filters are treated as `eq` comparisons.

## Relationship-path filters

```http
GET /customers?filter[computers.serial]=ABC-123
GET /computers?filter[owner.id]=1
```

## Common operators (Django ORM mapping)

- `eq`, `ne`
- `lt`, `le`, `gt`, `ge`
- `in`, `not_in`
- `like`, `ilike`
- `is_null`

## Logical combinations

Logical filter trees are supported via `and`, `or`, and `not` groups.

```json
[
	{"name": "status", "op": "eq", "val": "active"},
	{
		"or": [
			{"name": "age", "op": "gt", "val": 30},
			{"name": "role", "op": "eq", "val": "admin"}
		]
	},
	{
		"not": {
			"name": "deleted_at",
			"op": "is_null",
			"val": false
		}
	}
]
```

Top-level filter list items are still AND-combined in order.

## Notes

- URL-encode JSON values in production clients.
- Supported operators are data-layer specific.

