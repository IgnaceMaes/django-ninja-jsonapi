# API filtering example

This page shows query patterns supported by `QueryStringManager` and consumed by the Django ORM data layer.

## Full filter syntax

```http
GET /customers?filter=[{"name":"name","op":"eq","val":"John"}]
```

```http
GET /customers?filter=[{"name":"created_at","op":"ge","val":"2025-01-01"}]
```

## Simple filter syntax

```http
GET /customers?filter[name]=John
GET /customers?filter[name]=John&filter[is_active]=true
```

## Relationship-style field path

```http
GET /customers?filter[group.id]=1
GET /computers?filter[owner.email]=john@example.com
```

## Combined with sort + pagination

```http
GET /customers?filter[status]=active&sort=-created_at&page[size]=20&page[number]=1
```

```python
import httpx

response = httpx.get(
	"http://localhost:8000/api/customers",
	params={
		"filter[status]": "active",
		"sort": "-created_at",
		"page[size]": 20,
		"page[number]": 1,
	},
)
print(response.json())
```

## Response excerpt

```json
{
	"links": {
		"self": "http://localhost:8000/api/customers?filter%5Bstatus%5D=active&sort=-created_at&page%5Bsize%5D=20&page%5Bnumber%5D=1"
	},
	"data": [
		{
			"type": "customer",
			"id": "1",
			"attributes": {
				"name": "John",
				"status": "active"
			},
			"links": {
				"self": "http://localhost:8000/api/customers/1/"
			}
		}
	]
}
```

## Notes

- Keep `filter` URL-encoded in real clients.
- Supported operators depend on your data-layer mapping.
