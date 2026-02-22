# Atomic operations

Atomic operations allow multiple mutations in one request and execute them transactionally.

## Supported actions

- `add`
- `update`
- `remove`

## Endpoint

Default route:

```http
POST /operations
```

## Behavior

- Operations run in order.
- If one operation fails, all operations in the request are rolled back.

## Notes

- Keep payloads close to JSON:API Atomic Operations shape.
- Validate behavior against your model relationship complexity with integration tests.
