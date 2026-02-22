# Data layer

The data layer is the CRUD boundary between view orchestration and persistence.

## Responsibilities

- resource create/read/update/delete
- relationship linkage operations
- filter/sort/pagination translation

## Current implementation

- Django ORM is the only supported persistence backend.
- Query translation is implemented in `data_layers/django_orm`.

## Extension path

You can subclass or replace data-layer classes when custom storage behavior is needed.

## Example: custom data layer

Snippet file: `docs/python_snippets/data_layer/custom_data_layer.py`

```python
from django_ninja_jsonapi.data_layers.django_orm.orm import DjangoORMDataLayer


class TenantAwareDataLayer(DjangoORMDataLayer):
	async def get_collection(self, qs, relationship_request_info=None):
		base_qs = self.model.objects.filter(tenant_id=self.kwargs["tenant_id"])
		return await super().get_collection(qs=qs, relationship_request_info=relationship_request_info, base_qs=base_qs)
```

Then bind it on your view:

```python
from django_ninja_jsonapi import ViewBaseGeneric


class UserView(ViewBaseGeneric):
	data_layer_cls = TenantAwareDataLayer
```
