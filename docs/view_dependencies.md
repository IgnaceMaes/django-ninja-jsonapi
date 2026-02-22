# View dependencies

View dependencies let you compute request-time context and feed it into view/data-layer execution.

## Typical use cases

- permission checks
- tenant scoping
- per-request data-layer kwargs

## Pattern

Define operation-specific configuration that gathers dependency inputs and merges them into runtime kwargs.

Use this mechanism for request-scoped behavior instead of hard-coding globals in the data layer.
