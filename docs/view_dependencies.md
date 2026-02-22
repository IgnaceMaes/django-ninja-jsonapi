# View dependencies

View dependencies let you compute request-time context and feed it into view/data-layer execution.

## Typical use cases

- permission checks
- tenant scoping
- per-request data-layer kwargs

## Pattern

Define operation-specific configuration that gathers dependency inputs and merges them into runtime kwargs.

Use this mechanism for request-scoped behavior instead of hard-coding globals in the data layer.

## Example

Snippet files:

- `docs/python_snippets/view_dependencies/main_example.py`
- `docs/python_snippets/view_dependencies/several_dependencies.py`

```python
from pydantic import BaseModel

from django_ninja_jsonapi.views import Operation, OperationConfig
from django_ninja_jsonapi import ViewBaseGeneric


class RequestContext(BaseModel):
	tenant_id: str = "tenant-1"


def common_handler(view, dto: RequestContext) -> dict:
	return {
		"tenant_id": dto.tenant_id,
	}


class UserView(ViewBaseGeneric):
	operation_dependencies = {
		Operation.ALL: OperationConfig(
			dependencies=RequestContext,
			prepare_data_layer_kwargs=common_handler,
		),
	}
```

In this setup, your data layer receives `tenant_id` for each operation.
