from app.models import Customer
from app.schemas import CustomerSchema
from ninja import NinjaAPI

from django_ninja_jsonapi import ApplicationBuilder, ViewBaseGeneric


class CustomerView(ViewBaseGeneric):
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

builder.initialize()
