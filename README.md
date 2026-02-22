# django-ninja-jsonapi

JSON:API toolkit for Django Ninja.

[![CI](https://github.com/ignacemaes/django-ninja-jsonapi/actions/workflows/ci.yml/badge.svg)](https://github.com/ignacemaes/django-ninja-jsonapi/actions/workflows/ci.yml)
[![Package](https://github.com/ignacemaes/django-ninja-jsonapi/actions/workflows/package.yml/badge.svg)](https://github.com/ignacemaes/django-ninja-jsonapi/actions/workflows/package.yml)

This project ports the core ideas of `fastapi-jsonapi` to a Django Ninja + Django ORM stack.

Full documentation is available in [docs/index.md](docs/index.md).

## Status

- Working baseline for resource registration and route generation (`GET`, `GET LIST`, `POST`, `PATCH`, `DELETE`).
- Query parsing for JSON:API-style `filter`, `sort`, `include`, `fields`, and `page` parameters.
- JSON:API exception payload handling.
- Atomic operations endpoint wiring (`/operations`).
- Django ORM data-layer baseline for CRUD + basic relationship handling.

## Requirements

- Python 3.10+
- Django 4.2+
- Django Ninja 1.0+

## Install (uv)

```bash
uv sync
```

## Quick start

### 1) Define a Django model and a schema

```python
from django.db import models
from pydantic import BaseModel


class User(models.Model):
    name = models.CharField(max_length=128)


class UserSchema(BaseModel):
    name: str
```

### 2) Create a JSON:API view class

```python
from django_ninja_jsonapi import ViewBaseGeneric


class UserView(ViewBaseGeneric):
    pass
```

### 3) Register resources with `ApplicationBuilder`

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

### 4) Mount API in Django URLs

```python
from django.urls import path
from .api import api

urlpatterns = [
    path("api/", api.urls),
]
```

## Configuration

Set JSON:API options in Django settings:

```python
JSONAPI = {
    "MAX_INCLUDE_DEPTH": 3,
    "MAX_PAGE_SIZE": 100,
    "ALLOW_DISABLE_PAGINATION": True,
}
```

## Exported public API

```python
from django_ninja_jsonapi import ApplicationBuilder, QueryStringManager, HTTPException, BadRequest, ViewBaseGeneric
```

## Development

```bash
uv run ruff format src tests
uv run ruff check src tests
uv run pytest --cov=src/django_ninja_jsonapi --cov-report=term-missing
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full contribution workflow.

## Test coverage

Current tests cover:

- Application builder initialization and route registration behavior
- Query-string parsing behavior
- Django ORM query-building mapping (`filter`/`sort` translation)
- Exception handler response shape

## Notes

- This project is Django Ninja + Django ORM focused.
- SQLAlchemy-specific modules have been removed to keep the codebase simpler and consistent.
- CI runs on pull requests and pushes to `main`.
