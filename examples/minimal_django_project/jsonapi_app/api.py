from django_ninja_jsonapi import NinjaJsonAPI, apply_attributes, get_rel_id, jsonapi_paginate

from .models import Computer, Customer
from .schemas import ComputerSchema, ComputerSchemaIn, CustomerSchema, CustomerSchemaIn

api = NinjaJsonAPI(title="django-ninja-jsonapi minimal example")


# ---- Customers ----


@api.get("/customers", response=list[CustomerSchema], tags=["customers"])
def list_customers(request):
    return jsonapi_paginate(request, Customer.objects.order_by("id"))


@api.get("/customers/{customer_id}", response=CustomerSchema, tags=["customers"])
def get_customer(request, customer_id: int):
    return Customer.objects.prefetch_related("computers").get(pk=customer_id)


@api.post("/customers", response={201: CustomerSchema}, tags=["customers"])
def create_customer(request, body: CustomerSchemaIn):
    customer = Customer.objects.create(**body.model_dump())
    return 201, customer


@api.patch("/customers/{customer_id}", response=CustomerSchema, tags=["customers"])
def update_customer(request, customer_id: int, body: CustomerSchemaIn):
    customer = Customer.objects.get(pk=customer_id)
    apply_attributes(customer, body)
    return customer


@api.delete("/customers/{customer_id}", response={204: None}, tags=["customers"])
def delete_customer(request, customer_id: int):
    Customer.objects.get(pk=customer_id).delete()
    return 204, None


# ---- Computers ----


@api.get("/computers", response=list[ComputerSchema], tags=["computers"])
def list_computers(request):
    return jsonapi_paginate(request, Computer.objects.order_by("id"))


@api.get("/computers/{computer_id}", response=ComputerSchema, tags=["computers"])
def get_computer(request, computer_id: int):
    return Computer.objects.get(pk=computer_id)


@api.post("/computers", response={201: ComputerSchema}, tags=["computers"])
def create_computer(request, body: ComputerSchemaIn):
    owner_id = get_rel_id(request, "owner")
    computer = Computer.objects.create(**body.model_dump(), owner_id=owner_id)
    return 201, computer


@api.delete("/computers/{computer_id}", response={204: None}, tags=["computers"])
def delete_computer(request, computer_id: int):
    Computer.objects.get(pk=computer_id).delete()
    return 204, None
