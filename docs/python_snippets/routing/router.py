from ninja import NinjaAPI

from django_ninja_jsonapi import ApplicationBuilder
from django_ninja_jsonapi import ViewBaseGeneric

from app.models import User
from app.schemas import UserSchema


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
