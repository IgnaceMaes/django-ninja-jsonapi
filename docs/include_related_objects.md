# Include related objects

Use `include` to request related resources in the response `included` section.

## Basic include

```http
GET /customers/1?include=computers
```

```python
import httpx

response = httpx.get("http://localhost:8000/api/customers/1?include=computers")
data = response.json()
print(data.get("included", []))
```

Example response shape:

```json
{
	"data": {
		"type": "customer",
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
GET /customers/1?include=computers.owner
```

## Include with sparse fieldsets

```http
GET /customers/1?include=computers&fields[customer]=name,computers&fields[computer]=serial
```

```python
import httpx

url = "http://localhost:8000/api/customers/1?include=computers&fields[customer]=name,computers&fields[computer]=serial"
response = httpx.get(url)
print(response.json())
```

## Notes

- `include` works on endpoints that return resource data.
- Maximum depth is controlled by configuration (`MAX_INCLUDE_DEPTH`).
