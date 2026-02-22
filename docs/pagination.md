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

## Cursor pagination

```http
GET /customers?page[cursor]=100&page[size]=10
```

Cursor pagination uses keyset-style paging by resource id and returns `links.next` when more rows are available.

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
	"links": {
		"self": "http://localhost:8000/api/customers?page%5Bsize%5D=10&page%5Bnumber%5D=2",
		"first": "http://localhost:8000/api/customers?page%5Bnumber%5D=1&page%5Bsize%5D=10",
		"last": "http://localhost:8000/api/customers?page%5Bnumber%5D=4&page%5Bsize%5D=10",
		"prev": "http://localhost:8000/api/customers?page%5Bnumber%5D=1&page%5Bsize%5D=10",
		"next": "http://localhost:8000/api/customers?page%5Bnumber%5D=3&page%5Bsize%5D=10"
	},
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

This only works when `NINJA_JSONAPI["ALLOW_DISABLE_PAGINATION"]` is `True`.
