from ninja import NinjaAPI

from django_ninja_jsonapi import ApplicationBuilder, ViewBaseGeneric

from app.models import Computer, User
from app.schemas import ComputerSchema, UserSchema


class UserView(ViewBaseGeneric):
    pass


class ComputerView(ViewBaseGeneric):
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

builder.add_resource(
    path="/computers",
    tags=["computers"],
    resource_type="computer",
    view=ComputerView,
    model=Computer,
    schema=ComputerSchema,
)

builder.initialize()
