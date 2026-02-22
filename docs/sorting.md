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
