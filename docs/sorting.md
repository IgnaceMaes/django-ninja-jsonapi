# Sorting

Use the `sort` query parameter.

## Single field

```http
GET /customers?sort=name
```

## Multiple fields

```http
GET /customers?sort=name,created_at
```

## Descending

```http
GET /customers?sort=-name
GET /customers?sort=-name,created_at
```

```python
import httpx

response = httpx.get("http://localhost:8000/api/customers", params={"sort": "-name,created_at"})
print(response.json())
```

## Relationship path sorting

```http
GET /computers?sort=owner.name
GET /computers?sort=-owner.name,serial
```

## Practical examples

- Newest-first customers: `GET /customers?sort=-id`
- Owner then serial: `GET /computers?sort=owner.name,serial`
