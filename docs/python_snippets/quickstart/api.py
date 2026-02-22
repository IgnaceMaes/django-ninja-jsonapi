from ninja import NinjaAPI

from django_ninja_jsonapi import ApplicationBuilder, ViewBaseGeneric

from app.models import Computer, Customer
from app.schemas import ComputerSchema, CustomerSchema


class CustomerView(ViewBaseGeneric):
    pass


class ComputerView(ViewBaseGeneric):
    pass


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

builder.add_resource(
    path="/computers",
    tags=["computers"],
    resource_type="computer",
    view=ComputerView,
    model=Computer,
    schema=ComputerSchema,
)

builder.initialize()
