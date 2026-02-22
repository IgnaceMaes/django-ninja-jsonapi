# Quickstart

This guide walks through a full resource setup and the generated JSON:API-style endpoints.

## 1) Install

```bash
uv sync
```

## 2) Define model + schema

```python
from django.db import models
from pydantic import BaseModel


class User(models.Model):
    name = models.CharField(max_length=128)
    email = models.EmailField()


class UserSchema(BaseModel):
    name: str
    email: str
```

## 3) Define view

```python
from django_ninja_jsonapi import ViewBaseGeneric


class UserView(ViewBaseGeneric):
    pass
```

## 4) Register resource

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

builder.initialize()
```

## 5) Mount URLs

```python
from django.urls import path
from .api import api

urlpatterns = [path("api/", api.urls)]
```

## 6) Run and call endpoints

```bash
uv run python manage.py runserver
```

Common generated routes:

- `GET /api/users`
- `POST /api/users`
- `GET /api/users/{id}`
- `PATCH /api/users/{id}`
- `DELETE /api/users/{id}`

Relationship and relationship-link routes are generated when schema relationship metadata is available.
