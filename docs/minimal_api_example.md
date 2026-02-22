# Minimal API example

Build a minimal app with one resource and run real calls against it.

## API setup

```python
from ninja import NinjaAPI
from pydantic import BaseModel

from django_ninja_jsonapi import ApplicationBuilder, ViewBaseGeneric


class UserSchema(BaseModel):
    id: int
    name: str


class UserView(ViewBaseGeneric):
    pass

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

## URLConf

```python
from django.urls import path
from .api import api

urlpatterns = [
    path("api/", api.urls),
]
```

## Generated endpoints (example)

For a resource at `/users`, the builder generates standard routes such as:

- `GET /users`
- `POST /users`
- `GET /users/{id}`
- `PATCH /users/{id}`
- `DELETE /users/{id}`

## Request samples

```http
GET /api/users?page[size]=10&page[number]=1
```

```http
POST /api/users
Content-Type: application/json

{
    "data": {
        "type": "user",
        "attributes": {
            "name": "Jane"
        }
    }
}
```
