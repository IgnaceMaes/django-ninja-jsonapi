# Minimal API example

Build a minimal app with one resource and run real calls against it.

## API setup

```python
from ninja import NinjaAPI
from pydantic import BaseModel

from django_ninja_jsonapi import ApplicationBuilder, ViewBaseGeneric


class CustomerSchema(BaseModel):
    id: int
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

## URLConf

```python
from django.urls import path
from .api import api

urlpatterns = [
    path("api/", api.urls),
]
```

## Generated endpoints (example)

For a resource at `/customers`, the builder generates standard routes such as:

- `GET /customers`
- `POST /customers`
- `GET /customers/{id}`
- `PATCH /customers/{id}`
- `DELETE /customers/{id}`

## Request samples

```http
GET /api/customers?page[size]=10&page[number]=1
```

```http
POST /api/customers
Content-Type: application/json

{
    "data": {
        "type": "customer",
        "attributes": {
            "name": "Jane"
        }
    }
}
```
