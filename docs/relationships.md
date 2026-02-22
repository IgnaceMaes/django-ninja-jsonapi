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

- `GET /customers/{id}/computers`
- `GET /customers/{id}/relationships/computers`
- `POST/PATCH/DELETE /customers/{id}/relationships/computers`

```http
GET /customers/1/relationships/computers
```

```http
PATCH /customers/1/relationships/computers
Content-Type: application/json

{
	"data": [
		{"type": "computer", "id": "10"},
		{"type": "computer", "id": "11"}
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
