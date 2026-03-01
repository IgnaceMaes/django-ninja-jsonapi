# Relationships

Define relationships in resource schemas so the builder can expose related and relationship-link endpoints.

## Schema example

Snippet files:

- `docs/python_snippets/relationships/models.py`
- `docs/python_snippets/relationships/relationships_info_example.py`

```python
from typing import Annotated, Optional

from pydantic import BaseModel

from django_ninja_jsonapi.types_metadata import RelationshipInfo


class ComputerSchema(BaseModel):
	id: int
	serial: str
	owner: Annotated[
		Optional["CustomerSchema"],
		RelationshipInfo(resource_type="customer", many=False),
	] = None


class CustomerSchema(BaseModel):
	id: int
	name: str
	computers: Annotated[
		list[ComputerSchema],
		RelationshipInfo(resource_type="computer", many=True),
	] = []
```

## Why relationship metadata matters

Relationship metadata drives:

- relationship route generation
- include expansion
- relationship link payloads

## Typical endpoints and calls

`ApplicationBuilder` auto-generates all relationship endpoints based on `RelationshipInfo` metadata:

| Method   | URL pattern                                        | To-one | To-many |
| -------- | -------------------------------------------------- | :----: | :-----: |
| `GET`    | `/{id}/relationships/{relationship}`               | ✓      | ✓       |
| `POST`   | `/{id}/relationships/{relationship}`               |        | ✓       |
| `PATCH`  | `/{id}/relationships/{relationship}`               | ✓      | ✓       |
| `DELETE` | `/{id}/relationships/{relationship}`               |        | ✓       |
| `GET`    | `/{id}/{relationship}`                             | ✓      | ✓       |

To-one relationships only receive `PATCH` (replace), while to-many relationships additionally receive `POST` (add members) and `DELETE` (remove members).

### Read a relationship

```http
GET /customers/1/relationships/computers
```

### Replace a relationship (PATCH)

```http
PATCH /customers/1/relationships/computers
Content-Type: application/vnd.api+json

{
	"data": [
		{"type": "computer", "id": "10"},
		{"type": "computer", "id": "11"}
	]
}
```

### Add to a to-many relationship (POST)

```http
POST /customers/1/relationships/computers
Content-Type: application/vnd.api+json

{
	"data": [
		{"type": "computer", "id": "12"}
	]
}
```

### Remove from a to-many relationship (DELETE)

```http
DELETE /customers/1/relationships/computers
Content-Type: application/vnd.api+json

{
	"data": [
		{"type": "computer", "id": "10"}
	]
}
```

## Response links

Relationship payloads include JSON:API links:

```json
{
	"data": [
		{"type": "computer", "id": "10"}
	],
	"links": {
		"self": "http://localhost:8000/api/customers/1/relationships/computers/",
		"related": "http://localhost:8000/api/customers/1/computers/"
	}
}
```

Resource objects also include `links.self` in list/detail responses.
