# Relationships

Define relationships in resource schemas so the builder can expose related and relationship-link endpoints.

## Why relationship metadata matters

Relationship metadata drives:

- relationship route generation
- include expansion
- relationship link payloads

## Typical endpoints

- `GET /users/{id}/computers`
- `GET /users/{id}/relationships/computers`
- `POST/PATCH/DELETE /users/{id}/relationships/computers`
