# django-ninja-jsonapi

JSON:API toolkit for Django Ninja.

[![CI](https://github.com/ignacemaes/django-ninja-jsonapi/actions/workflows/ci.yml/badge.svg)](https://github.com/ignacemaes/django-ninja-jsonapi/actions/workflows/ci.yml)
[![Package](https://github.com/ignacemaes/django-ninja-jsonapi/actions/workflows/package.yml/badge.svg)](https://github.com/ignacemaes/django-ninja-jsonapi/actions/workflows/package.yml)

This project ports the core ideas of `fastapi-jsonapi` to a Django Ninja + Django ORM stack, following the [JSON:API specification](https://jsonapi.org/).

Full documentation is available in [docs/index.md](docs/index.md).

## Status

- Working baseline for resource registration and route generation (`GET`, `GET LIST`, `POST`, `PATCH`, `DELETE`).
- Strict query parsing for JSON:API-style `filter`, `sort`, `include`, `fields`, and `page` parameters.
- JSON:API exception payload handling.
- Atomic operations endpoint wiring (`/operations`).
- Django ORM data-layer baseline for CRUD + basic relationship handling.
- Top-level/resource/relationship `links` in responses.
- Django ORM include optimization (`select_related`/`prefetch_related` split) with optional include mapping overrides.
- Logical filter groups (`and`/`or`/`not`) and cursor pagination (`page[cursor]`).

## Requirements

- Python 3.10+
- Django 4.2+
- Django Ninja 1.0+

## Install

```bash
uv add django-ninja-jsonapi
```

or

- `pip install django-ninja-jsonapi`
- `poetry add django-ninja-jsonapi`
- `pdm add django-ninja-jsonapi`

## Quick start

### 1) Define a Django model and a schema

```python
from django.db import models
from pydantic import BaseModel


class Customer(models.Model):
    name = models.CharField(max_length=128)


class CustomerSchema(BaseModel):
    name: str
```

### 2) Create a JSON:API view class

```python
from django_ninja_jsonapi import ViewBaseGeneric


class CustomerView(ViewBaseGeneric):
    pass
```

### 3) Register resources with `ApplicationBuilder`

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
NINJA_JSONAPI = {
    "MAX_INCLUDE_DEPTH": 3,
    "MAX_PAGE_SIZE": 20,
    "ALLOW_DISABLE_PAGINATION": True,
    "INCLUDE_JSONAPI_OBJECT": False,
    "JSONAPI_VERSION": "1.0",
}
```

Additional view/schema options:

- `django_filterset_class` on a `ViewBaseGeneric` subclass to enable optional django-filter integration.
- `JSONAPIMeta.meta_fields` (or `Meta.meta_fields`) on schema classes to expose selected fields in resource `meta`.

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

## Release process

Releases are automated with GitHub Actions:

1. Merge conventional-commit PRs into `main`.
2. `Release Please` opens or updates a release PR with version bump + changelog updates.
3. Merge the release PR to create a GitHub Release.
4. `Publish to PyPI` runs on `release: published` and uploads the built package to PyPI.

Workflows:

- `.github/workflows/release-please.yml`
- `.github/workflows/publish.yml`

Required repository secrets:

- `REPO_ADMIN_TOKEN` (used by Release Please)
- `PYPI_API_TOKEN` (used for PyPI publishing)

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
