from ninja import NinjaAPI
from pydantic import BaseModel

from django_ninja_jsonapi import JSONAPIRenderer, jsonapi_include, jsonapi_meta, jsonapi_paginate, jsonapi_resource

from .models import Customer


class CustomerStandaloneSchema(BaseModel):
    id: int
    name: str
    email: str


api = NinjaAPI(
    title="django-ninja-jsonapi standalone renderer example",
    urls_namespace="api-standalone",
    renderer=JSONAPIRenderer(),
)


@api.get("/customers", response=list[CustomerStandaloneSchema], tags=["standalone-customers"])
@jsonapi_resource("customer")
def list_customers(request):
    return jsonapi_paginate(request, Customer.objects.order_by("id"))


@api.get("/customers/{customer_id}", response=CustomerStandaloneSchema, tags=["standalone-customers"])
@jsonapi_resource(
    "customer",
    relationships={
        "computers": {"resource_type": "computer", "many": True},
    },
)
def get_customer(request, customer_id: int):
    customer = Customer.objects.get(id=customer_id)
    computers = [{"id": computer.id, "serial": computer.serial} for computer in customer.computers.order_by("id")]
    jsonapi_include(request, computers, resource_type="computer")
    jsonapi_meta(request, included_count=len(computers))

    return {
        "id": customer.id,
        "name": customer.name,
        "email": customer.email,
        "computers": [{"id": computer["id"]} for computer in computers],
    }
