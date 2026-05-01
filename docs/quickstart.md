# Quickstart

Get a JSON:API endpoint running in three steps.

## 1) Define a Django model and schemas

```python
from typing import ClassVar

from django.db import models
from pydantic import BaseModel

from django_ninja_jsonapi import JsonApiMeta


class Customer(models.Model):
    name = models.CharField(max_length=128)


class CustomerSchema(BaseModel):
    id: int
    name: str

    jsonapi_meta: ClassVar[JsonApiMeta] = JsonApiMeta(resource_type="customers")


class CustomerCreateSchema(BaseModel):
    name: str
```

## 2) Create your API with `NinjaJsonAPI`

```python
from django_ninja_jsonapi import NinjaJsonAPI

api = NinjaJsonAPI()


@api.get("/customers", response=list[CustomerSchema])
def list_customers(request):
    return Customer.objects.all()


@api.get("/customers/{customer_id}", response=CustomerSchema)
def get_customer(request, customer_id: int):
    return Customer.objects.get(pk=customer_id)


@api.post("/customers", response={201: CustomerSchema})
def create_customer(request, body: CustomerCreateSchema):
    customer = Customer.objects.create(**body.model_dump())
    return 201, customer
```

## 3) Mount API in Django URLs

```python
from django.urls import path
from .api import api

urlpatterns = [
    path("api/", api.urls),
]
```

## Example responses

`GET /api/customers/1`

```json
{
  "data": {
    "type": "customers",
    "id": "1",
    "attributes": {
      "name": "Alice"
    }
  }
}
```

`GET /api/customers`

```json
{
  "data": [
    {
      "type": "customers",
      "id": "1",
      "attributes": { "name": "Alice" }
    },
    {
      "type": "customers",
      "id": "2",
      "attributes": { "name": "Bob" }
    }
  ]
}
```

Resources have a `type` and `id` at the top level while model fields are nested under `attributes`.
Relationships, includes, sparse fieldsets, filtering, sorting, and pagination all follow the [JSON:API specification](https://jsonapi.org/format/).

## What's next

- [Configuration](configuration.md) — tweak pagination limits, inflection, and more.
- [Filtering](filtering.md) — add `?filter[name]=Alice` support.
- [Include related objects](include_related_objects.md) — sideload relationships with `?include=`.
