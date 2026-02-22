# API filtering example

This page shows query patterns supported by `QueryStringManager` and consumed by the Django ORM data layer.

## Full filter syntax

```http
GET /users?filter=[{"name":"name","op":"eq","val":"John"}]
```

```http
GET /users?filter=[{"name":"created_at","op":"ge","val":"2025-01-01"}]
```

## Simple filter syntax

```http
GET /users?filter[name]=John
GET /users?filter[name]=John&filter[is_active]=true
```

## Relationship-style field path

```http
GET /users?filter[group.id]=1
GET /computers?filter[owner.email]=john@example.com
```

## Combined with sort + pagination

```http
GET /users?filter[status]=active&sort=-created_at&page[size]=20&page[number]=1
```

## Response excerpt

```json
{
	"data": [
		{
			"type": "user",
			"id": "1",
			"attributes": {
				"name": "John",
				"status": "active"
			}
		}
	]
}
```

## Notes

- Keep `filter` URL-encoded in real clients.
- Supported operators depend on your data-layer mapping.
