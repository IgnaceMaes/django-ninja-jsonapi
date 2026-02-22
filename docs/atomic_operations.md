# Atomic operations

Atomic operations allow multiple mutations in one request and execute them transactionally.

## Supported actions

- `add`
- `update`
- `remove`

## Endpoint

Default route:

```http
POST /operations
```

## Request example (mixed actions)

```http
POST /operations
Content-Type: application/json

{
	"atomic:operations": [
		{
			"op": "add",
			"data": {
				"type": "customer",
				"lid": "customer-1",
				"attributes": {"name": "John", "email": "john@example.com"}
			}
		},
		{
			"op": "add",
			"data": {
				"type": "computer",
				"attributes": {"serial": "ABC-123"},
				"relationships": {
					"owner": {
						"data": {"type": "customer", "lid": "customer-1"}
					}
				}
			}
		}
	]
}
```

```python
import httpx

payload = {
	"atomic:operations": [
		{
			"op": "add",
			"data": {
				"type": "customer",
				"lid": "customer-1",
				"attributes": {"name": "John", "email": "john@example.com"},
			},
		},
		{
			"op": "add",
			"data": {
				"type": "computer",
				"attributes": {"serial": "ABC-123"},
				"relationships": {"owner": {"data": {"type": "customer", "lid": "customer-1"}}},
			},
		},
	]
}

response = httpx.post("http://localhost:8000/operations", json=payload)
print(response.status_code, response.json())
```

## Response example

```json
{
	"atomic:results": [
		{"data": {"type": "customer", "id": "1"}},
		{"data": {"type": "computer", "id": "10"}}
	]
}
```

## Behavior

- Operations run in order.
- If one operation fails, all operations in the request are rolled back.

## Notes

- Keep payloads close to JSON:API Atomic Operations shape.
- Validate behavior against your model relationship complexity with integration tests.
