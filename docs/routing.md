# Routing

`ApplicationBuilder` generates Django Ninja routes from resource registration metadata.

## Resource routes

For each resource, the builder creates list/detail CRUD endpoints and relationship endpoints when relationship metadata is available.

## Path conventions

- Resource collection: `/resource-path`
- Resource detail: `/resource-path/{id}`
- Related resources: `/resource-path/{id}/{relationship}`
- Relationship links: `/resource-path/{id}/relationships/{relationship}`

## Atomic route

When atomic support is initialized, the default endpoint is:

- `POST /operations`
