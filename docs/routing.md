# Routing

`ApplicationBuilder` generates Django Ninja routes from resource registration metadata.

## Resource registration example

Snippet file: `docs/python_snippets/routing/router.py`

```python
builder.add_resource(
	path="/customers",
	tags=["customers"],
	resource_type="customer",
	view=CustomerView,
	model=Customer,
	schema=CustomerSchema,
)
```

For each resource, the builder creates list/detail CRUD endpoints and relationship endpoints when relationship metadata exists.
Collection `DELETE` is not registered by default; include `Operation.DELETE_LIST` explicitly when needed.

## Path conventions

- Resource collection: `/resource-path`
- Resource detail: `/resource-path/{id}`
- Related resources: `/resource-path/{id}/{relationship}`
- Relationship links: `/resource-path/{id}/relationships/{relationship}`

## Route map (example)

For `/customers`:

- `GET /customers/` → list
- `POST /customers/` → create
- `GET /customers/{obj_id}/` → detail
- `PATCH /customers/{obj_id}/` → update
- `DELETE /customers/{obj_id}/` → delete

For relationship `computers` on customer:

- `GET /customers/{obj_id}/computers/`
- `GET /customers/{obj_id}/relationships/computers/`

## Atomic route

When atomic support is initialized, the default endpoint is:

- `POST /operations`

You can customize this by creating `AtomicOperations(url_path="/atomic")` and including its router.
