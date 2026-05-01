from ninja import NinjaAPI
from pydantic import BaseModel, ConfigDict

from django_ninja_jsonapi import JSONAPIRenderer, jsonapi_include, jsonapi_meta, jsonapi_paginate
from django_ninja_jsonapi.renderers import (
    REQUEST_JSONAPI_CONFIG_ATTR,
    JSONAPIRelationshipConfig,
    JSONAPIResourceConfig,
)
from django_ninja_jsonapi.schema_factory import jsonapi_response

from .models import Customer


class CustomerStandaloneSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str


CUSTOMER_RELATIONSHIPS = {
    "computers": JSONAPIRelationshipConfig(resource_type="computers", many=True),
}

api = NinjaAPI(
    title="django-ninja-jsonapi standalone renderer example",
    urls_namespace="api-standalone",
    renderer=JSONAPIRenderer(),
)


@api.get(
    "/customers",
    response=jsonapi_response(CustomerStandaloneSchema, "customers", many=True),
    tags=["standalone-customers"],
)
def list_customers(request):
    setattr(request, REQUEST_JSONAPI_CONFIG_ATTR, JSONAPIResourceConfig(resource_type="customers"))
    return jsonapi_paginate(request, Customer.objects.order_by("id"))


@api.get(
    "/customers/{customer_id}",
    response=jsonapi_response(CustomerStandaloneSchema, "customers", relationships=CUSTOMER_RELATIONSHIPS),
    tags=["standalone-customers"],
)
def get_customer(request, customer_id: int):
    setattr(
        request,
        REQUEST_JSONAPI_CONFIG_ATTR,
        JSONAPIResourceConfig(resource_type="customers", relationships=CUSTOMER_RELATIONSHIPS),
    )
    customer = Customer.objects.get(id=customer_id)
    computers = [{"id": computer.id, "serial": computer.serial} for computer in customer.computers.order_by("id")]
    jsonapi_include(request, computers, resource_type="computers")
    jsonapi_meta(request, included_count=len(computers))

    return customer
