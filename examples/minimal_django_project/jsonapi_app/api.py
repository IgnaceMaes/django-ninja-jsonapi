from ninja import NinjaAPI

from django_ninja_jsonapi import ApplicationBuilder

from .models import Computer, User
from .schemas import ComputerSchema, ComputerSchemaIn, UserSchema, UserSchemaIn
from .views import ComputerView, UserView

api = NinjaAPI(title="django-ninja-jsonapi minimal example")
builder = ApplicationBuilder(api)

builder.add_resource(
    path="/users",
    tags=["users"],
    resource_type="user",
    view=UserView,
    model=User,
    schema=UserSchema,
    schema_in_post=UserSchemaIn,
    schema_in_patch=UserSchemaIn,
)

builder.add_resource(
    path="/computers",
    tags=["computers"],
    resource_type="computer",
    view=ComputerView,
    model=Computer,
    schema=ComputerSchema,
    schema_in_post=ComputerSchemaIn,
    schema_in_patch=ComputerSchemaIn,
)

builder.initialize()
