# Minimal Django project example

This example mirrors the upstream examples style with a small runnable API project.

## What it includes

- Django project config (`project/`)
- Example app (`jsonapi_app/`) with models, schemas, and views
- `django-ninja-jsonapi` `ApplicationBuilder` route registration

## Run locally

From repository root:

```bash
uv sync --dev
cd examples/minimal_django_project
uv run python manage.py makemigrations jsonapi_app
uv run python manage.py migrate
uv run python manage.py runserver
```

Open docs at:

- `http://127.0.0.1:8000/api/docs`

## Example requests

Create user:

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

Create computer:

```http
POST /api/computers
Content-Type: application/json

{
  "data": {
    "type": "computer",
    "attributes": {
      "serial": "ABC-123"
    }
  }
}
```

List users:

```http
GET /api/users
```
