# Quickstart

This guide shows a complete Django Ninja setup with two related resources (`user` and `computer`) and demonstrates CRUD + relationship workflows.

## 1) Install

```bash
uv sync
```

## 2) Define models

```python
from django.db import models


class User(models.Model):
    name = models.CharField(max_length=128)
    email = models.EmailField(unique=True)


class Computer(models.Model):
    serial = models.CharField(max_length=128)
    owner = models.ForeignKey(User, related_name="computers", null=True, blank=True, on_delete=models.SET_NULL)
```

## 3) Define JSON:API schemas (logical API layer)

```python
from typing import Annotated, Optional

from pydantic import BaseModel

from django_ninja_jsonapi.types_metadata import RelationshipInfo


class ComputerSchema(BaseModel):
    id: int
    serial: str
    owner: Annotated[
        Optional["UserSchema"],
        RelationshipInfo(resource_type="user", many=False),
    ] = None


class UserSchema(BaseModel):
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


class UserView(ViewBaseGeneric):
    pass


class ComputerView(ViewBaseGeneric):
    pass
```

## 5) Register resources

```python
from ninja import NinjaAPI
from django_ninja_jsonapi import ApplicationBuilder

api = NinjaAPI()
builder = ApplicationBuilder(api)

builder.add_resource(
    path="/users",
    tags=["users"],
    resource_type="user",
    view=UserView,
    model=User,
    schema=UserSchema,
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

For `/users`:

- `GET /api/users`
- `POST /api/users`
- `GET /api/users/{id}`
- `PATCH /api/users/{id}`
- `DELETE /api/users/{id}`

Relationship endpoints (from `RelationshipInfo`):

- `GET /api/users/{id}/computers`
- `GET /api/users/{id}/relationships/computers`

## Example requests

### Create user

```http
POST /api/users
Content-Type: application/json

{
    "data": {
        "type": "user",
        "attributes": {
            "name": "John",
            "email": "john@example.com"
        }
    }
}
```

### List users with related computers

```http
GET /api/users?include=computers&fields[user]=name,email,computers&fields[computer]=serial
```

### Update user

```http
PATCH /api/users/1
Content-Type: application/json

{
    "data": {
        "type": "user",
        "id": "1",
        "attributes": {
            "name": "John Updated"
        }
    }
}
```

Relationship and relationship-link routes are generated when schema relationship metadata is available.
