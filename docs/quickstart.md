# Quickstart

This guide shows a complete Django Ninja setup with two related resources (`customer` and `computer`) and demonstrates CRUD + relationship workflows.

## 1) Install

```bash
uv sync
```

## 2) Define models

Snippet file: `docs/python_snippets/quickstart/models.py`

```python
from django.db import models


class Customer(models.Model):
    name = models.CharField(max_length=128)
    email = models.EmailField(unique=True)


class Computer(models.Model):
    serial = models.CharField(max_length=128)
    owner = models.ForeignKey(Customer, related_name="computers", null=True, blank=True, on_delete=models.SET_NULL)
```

## 3) Define JSON:API schemas (logical API layer)

Snippet file: `docs/python_snippets/quickstart/schemas.py`

```python
from typing import Annotated, Optional

from pydantic import BaseModel

from django_ninja_jsonapi.types_metadata import RelationshipInfo


class ComputerSchema(BaseModel):
    id: int
    serial: str
    owner: Annotated[
        Optional["CustomerSchema"],
        RelationshipInfo(resource_type="customer", many=False),
    ] = None


class CustomerSchema(BaseModel):
    id: int
    name: str
    email: str
    computers: Annotated[
        list[ComputerSchema],
        RelationshipInfo(resource_type="computer", many=True),
    ] = []
```

## 4) Define views

```python
from django_ninja_jsonapi import ViewBaseGeneric


class CustomerView(ViewBaseGeneric):
    pass


class ComputerView(ViewBaseGeneric):
    pass
```

## 5) Register resources

Snippet file: `docs/python_snippets/quickstart/api.py`

```python
from ninja import NinjaAPI
from django_ninja_jsonapi import ApplicationBuilder

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

builder.add_resource(
    path="/computers",
    tags=["computers"],
    resource_type="computer",
    view=ComputerView,
    model=Computer,
    schema=ComputerSchema,
)

builder.initialize()
```

## 6) Mount URLs

```python
from django.urls import path
from .api import api

urlpatterns = [path("api/", api.urls)]
```

## 7) Run

```bash
uv run python manage.py runserver
```

## Generated endpoint shape

For `/customers`:

- `GET /api/customers`
- `POST /api/customers`
- `GET /api/customers/{id}`
- `PATCH /api/customers/{id}`
- `DELETE /api/customers/{id}`

Relationship endpoints (from `RelationshipInfo`):

- `GET /api/customers/{id}/computers`
- `GET /api/customers/{id}/relationships/computers`

## Example requests

### Create customer

JSON snippet: `docs/http_snippets/quickstart__create_customer.json`

```http
POST /api/customers
Content-Type: application/json

{
    "data": {
        "type": "customer",
        "attributes": {
            "name": "John",
            "email": "john@example.com"
        }
    }
}
```

### List customers with related computers

```http
GET /api/customers?include=computers&fields[customer]=name,email,computers&fields[computer]=serial
```

### Update customer

JSON snippet: `docs/http_snippets/quickstart__update_customer.json`

```http
PATCH /api/customers/1
Content-Type: application/json

{
    "data": {
        "type": "customer",
        "id": "1",
        "attributes": {
            "name": "John Updated"
        }
    }
}
```

Relationship and relationship-link routes are generated when schema relationship metadata is available.

## Response and query notes

- Responses include top-level `links` and resource-level `links.self`.
- Relationship payloads include `links.self` and `links.related`.
- Unknown query parameters return `400 Bad Request`.
