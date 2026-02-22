# Permission

Permission patterns are currently implemented through Django/Ninja dependencies and custom checks in view hooks.

## Example

```python
from pydantic import BaseModel

from django_ninja_jsonapi import ViewBaseGeneric
from django_ninja_jsonapi.exceptions import Forbidden
from django_ninja_jsonapi.views import Operation, OperationConfig


class AuthDependency(BaseModel):
	x_auth: str = ""


def check_admin(view, dto: AuthDependency) -> dict:
	if dto.x_auth != "admin":
		raise Forbidden(detail="Only admin can access this endpoint")
	return {}


class UserView(ViewBaseGeneric):
	operation_dependencies = {
		Operation.GET: OperationConfig(
			dependencies=AuthDependency,
			prepare_data_layer_kwargs=check_admin,
		),
	}
```

## Recommended approach

- enforce authentication/authorization with Django middleware and Ninja auth utilities
- add operation-level guards in view configuration/dependencies
- return JSON:API exceptions (`Forbidden`, `Unauthorized`) for uniform error payloads

Dedicated permission helper abstractions may be expanded in future releases.
