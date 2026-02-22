# Sorting

Use the `sort` query parameter.

## Single field

```http
GET /users?sort=name
```

## Multiple fields

```http
GET /users?sort=name,created_at
```

## Descending

```http
GET /users?sort=-name
GET /users?sort=-name,created_at
```

```python
import httpx

response = httpx.get("http://localhost:8000/api/users", params={"sort": "-name,created_at"})
print(response.json())
```

## Relationship path sorting

```http
GET /computers?sort=owner.name
GET /computers?sort=-owner.name,serial
```

## Practical examples

- Newest-first users: `GET /users?sort=-id`
- Owner then serial: `GET /computers?sort=owner.name,serial`
