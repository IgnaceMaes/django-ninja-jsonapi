# Minimal API example

Build a minimal app with one resource and mount it in Django URLs.

## API setup

```python
from ninja import NinjaAPI
from django_ninja_jsonapi import ApplicationBuilder, ViewBaseGeneric

api = NinjaAPI()
builder = ApplicationBuilder(api)

# register resources here...

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

## Generated endpoints

For a resource at `/users`, the builder generates standard routes such as:

- `GET /users`
- `POST /users`
- `GET /users/{id}`
- `PATCH /users/{id}`
- `DELETE /users/{id}`
