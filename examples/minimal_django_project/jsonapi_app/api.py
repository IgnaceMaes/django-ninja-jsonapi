from ninja import NinjaAPI

from django_ninja_jsonapi import ApplicationBuilder

from .models import Computer, Customer
from .schemas import ComputerSchema, ComputerSchemaIn, CustomerSchema, CustomerSchemaIn
from .views import ComputerView, CustomerView

api = NinjaAPI(title="django-ninja-jsonapi minimal example")
builder = ApplicationBuilder(api)

builder.add_resource(
    path="/customers",
    tags=["customers"],
    resource_type="customer",
    view=CustomerView,
    model=Customer,
    schema=CustomerSchema,
    schema_in_post=CustomerSchemaIn,
    schema_in_patch=CustomerSchemaIn,
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
