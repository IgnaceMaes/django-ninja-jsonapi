# Limited methods example

Use the `operations` argument in `ApplicationBuilder.add_resource` to expose only selected endpoints.

```python
from django_ninja_jsonapi.views.enums import Operation

builder.add_resource(
    path="/customers",
    tags=["customers"],
    resource_type="customer",
    view=CustomerView,
    model=Customer,
    schema=CustomerSchema,
    operations=[Operation.GET_LIST, Operation.GET],
)
```

In this case, write operations (`POST`, `PATCH`, `DELETE`) are not registered.
