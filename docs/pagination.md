# Pagination

Pagination uses the `page` query namespace.

## Page size

```http
GET /customers?page[size]=10
```

## Page number

```http
GET /customers?page[number]=2
```

## Combined

```http
GET /customers?page[size]=10&page[number]=2
```

```python
import httpx

response = httpx.get(
	"http://localhost:8000/api/customers",
	params={"page[size]": 10, "page[number]": 2},
)
payload = response.json()
print(payload.get("meta"))
```

Typical list response contains pagination metadata:

```json
{
	"data": [...],
	"meta": {
		"count": 10,
		"totalPages": 4
	}
}
```

## Disable pagination

Depending on configuration, pagination can be disabled with:

```http
GET /customers?page[size]=0
```

This only works when `JSONAPI["ALLOW_DISABLE_PAGINATION"]` is `True`.
