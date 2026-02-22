# Quickstart

## 1) Install dependencies

```bash
uv sync
```

## 2) Define model + schema

```python
from django.db import models
from pydantic import BaseModel


class User(models.Model):
    name = models.CharField(max_length=128)


class UserSchema(BaseModel):
    name: str
```

## 3) Define view class

```python
from django_ninja_jsonapi.generics import ViewBaseGeneric


class UserView(ViewBaseGeneric):
    pass
```

## 4) Register resource routes

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

## 5) Mount API in Django URLconf

```python
from django.urls import path
from .api import api

urlpatterns = [
    path("api/", api.urls),
]
```

## 6) Run

```bash
uv run python manage.py runserver
```

Open Django Ninja docs at `/api/docs`.
