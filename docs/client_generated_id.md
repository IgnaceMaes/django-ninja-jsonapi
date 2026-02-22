# Client-generated ID

JSON:API allows clients to send IDs during create requests in some workflows.

```python
from typing import Annotated

from pydantic import BaseModel

from django_ninja_jsonapi.types_metadata import ClientCanSetId


class UserSchema(BaseModel):
    id: Annotated[str, ClientCanSetId(cast_type=str)]
    name: str
    email: str
```

Create request example:

```http
POST /api/users
Content-Type: application/json

{
	"data": {
		"type": "user",
		"id": "external-user-123",
		"attributes": {
			"name": "John",
			"email": "john@example.com"
		}
	}
}
```

## Guidance

- Prefer server-generated IDs for most Django model setups.
- Enable client IDs only when your domain requires externally assigned identifiers.
- Validate uniqueness and ownership constraints at the data-layer boundary.

If enabled, treat client-provided IDs as untrusted input and enforce strict validation.
