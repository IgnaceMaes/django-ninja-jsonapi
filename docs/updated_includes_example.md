# Updated includes example

This example combines relationship updates with `include` to return expanded payloads in one call.

## Example flow

1. Update user attributes and relationships.
2. Pass `include=computers` to receive updated related resources immediately.
3. Read both `data` and `included` in one round-trip.

```http
PATCH /users/1?include=computers
Content-Type: application/json

{
	"data": {
		"type": "user",
		"id": "1",
		"attributes": {
			"name": "John Updated"
		},
		"relationships": {
			"computers": {
				"data": [{"type": "computer", "id": "10"}]
			}
		}
	}
}
```

Example response excerpt:

```json
{
	"data": {"type": "user", "id": "1"},
	"included": [
		{"type": "computer", "id": "10", "attributes": {"serial": "ABC-123"}}
	]
}
```

Use this pattern when clients need immediate post-update relationship context.
