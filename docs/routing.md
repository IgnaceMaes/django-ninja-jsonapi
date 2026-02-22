# Routing

`ApplicationBuilder` generates Django Ninja routes from resource registration metadata.

## Resource registration example

Snippet file: `docs/python_snippets/routing/router.py`

```python
builder.add_resource(
	path="/users",
	tags=["users"],
	resource_type="user",
	view=UserView,
	model=User,
	schema=UserSchema,
)
```

For each resource, the builder creates list/detail CRUD endpoints and relationship endpoints when relationship metadata exists.

## Path conventions

- Resource collection: `/resource-path`
- Resource detail: `/resource-path/{id}`
- Related resources: `/resource-path/{id}/{relationship}`
- Relationship links: `/resource-path/{id}/relationships/{relationship}`

## Route map (example)

For `/users`:

- `GET /users/` → list
- `POST /users/` → create
- `GET /users/{obj_id}/` → detail
- `PATCH /users/{obj_id}/` → update
- `DELETE /users/{obj_id}/` → delete

For relationship `computers` on user:

- `GET /users/{obj_id}/computers/`
- `GET /users/{obj_id}/relationships/computers/`

## Atomic route

When atomic support is initialized, the default endpoint is:

- `POST /operations`

You can customize this by creating `AtomicOperations(url_path="/atomic")` and including its router.
