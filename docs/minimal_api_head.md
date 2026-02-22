# Minimal API (head)

This is the smallest possible setup to register one JSON:API-style resource on Django Ninja.

Use this when you want a quick baseline before adding relationships, filters, and atomic operations.

```python
from ninja import NinjaAPI
from pydantic import BaseModel
from django.db import models

from django_ninja_jsonapi import ApplicationBuilder, ViewBaseGeneric


class User(models.Model):
    name = models.CharField(max_length=128)


class UserSchema(BaseModel):
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

Then mount with:

```python
urlpatterns = [
    path("api/", api.urls),
]
```
