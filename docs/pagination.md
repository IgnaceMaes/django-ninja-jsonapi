# Pagination

Pagination uses the `page` query namespace.

## Page size

```http
GET /users?page[size]=10
```

## Page number

```http
GET /users?page[number]=2
```

## Combined

```http
GET /users?page[size]=10&page[number]=2
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
GET /users?page[size]=0
```

This only works when `JSONAPI["ALLOW_DISABLE_PAGINATION"]` is `True`.
