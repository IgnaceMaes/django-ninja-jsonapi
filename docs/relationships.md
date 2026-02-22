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
		Optional["UserSchema"],
		RelationshipInfo(resource_type="user", many=False),
	] = None


class UserSchema(BaseModel):
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

- `GET /users/{id}/computers`
- `GET /users/{id}/relationships/computers`
- `POST/PATCH/DELETE /users/{id}/relationships/computers`

```http
GET /users/1/relationships/computers
```

```http
PATCH /users/1/relationships/computers
Content-Type: application/json

{
	"data": [
		{"type": "computer", "id": "10"},
		{"type": "computer", "id": "11"}
	]
}
```
