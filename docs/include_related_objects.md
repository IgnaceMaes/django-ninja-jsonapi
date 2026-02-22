# Include related objects

Use `include` to request related resources in the response `included` section.

## Basic include

```http
GET /users/1?include=computers
```

Example response shape:

```json
{
	"data": {
		"type": "user",
		"id": "1",
		"attributes": {"name": "John"},
		"relationships": {
			"computers": {
				"data": [{"type": "computer", "id": "10"}]
			}
		}
	},
	"included": [
		{
			"type": "computer",
			"id": "10",
			"attributes": {"serial": "ABC-123"}
		}
	]
}
```

## Nested include

```http
GET /users/1?include=computers.owner
```

## Include with sparse fieldsets

```http
GET /users/1?include=computers&fields[user]=name,computers&fields[computer]=serial
```

## Notes

- `include` works on endpoints that return resource data.
- Maximum depth is controlled by configuration (`MAX_INCLUDE_DEPTH`).
