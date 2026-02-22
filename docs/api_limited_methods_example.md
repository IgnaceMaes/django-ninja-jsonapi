# Limited methods example

Use the `operations` argument in `ApplicationBuilder.add_resource` to expose only selected endpoints.

```python
from django_ninja_jsonapi.views.enums import Operation

builder.add_resource(
    path="/users",
    tags=["users"],
    resource_type="user",
    view=UserView,
    model=User,
    schema=UserSchema,
    operations=[Operation.GET_LIST, Operation.GET],
)
```

In this case, write operations (`POST`, `PATCH`, `DELETE`) are not registered.
