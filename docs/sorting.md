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

## Relationship path sorting

```http
GET /computers?sort=owner.name
GET /computers?sort=-owner.name,serial
```

## Practical examples

- Newest-first users: `GET /users?sort=-id`
- Owner then serial: `GET /computers?sort=owner.name,serial`
