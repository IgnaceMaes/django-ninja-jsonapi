# Minimal API (head)

This is the smallest possible setup to register one JSON:API-style resource on Django Ninja.

Use this when you want a quick baseline before adding relationships, filters, and atomic operations.

```python
from ninja import NinjaAPI
from pydantic import BaseModel
from django.db import models

from django_ninja_jsonapi import ApplicationBuilder, ViewBaseGeneric


class Customer(models.Model):
    name = models.CharField(max_length=128)


class CustomerSchema(BaseModel):
    name: str


class CustomerView(ViewBaseGeneric):
    pass


api = NinjaAPI()
builder = ApplicationBuilder(api)
builder.add_resource(
    path="/customers",
    tags=["customers"],
    resource_type="customer",
    view=CustomerView,
    model=Customer,
    schema=CustomerSchema,
)
builder.initialize()
```

Then mount with:

```python
urlpatterns = [
    path("api/", api.urls),
]
```
