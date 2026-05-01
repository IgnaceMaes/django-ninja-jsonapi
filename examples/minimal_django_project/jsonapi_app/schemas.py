from pydantic import BaseModel

from django_ninja_jsonapi import ModelSchema

from .models import Computer, Customer


class CustomerSchema(ModelSchema):
    class Meta:
        model = Customer
        fields = ["id", "name", "email"]
        resource_type = "customers"


class ComputerSchema(ModelSchema):
    class Meta:
        model = Computer
        fields = ["id", "serial"]
        resource_type = "computers"


class CustomerSchemaIn(BaseModel):
    name: str
    email: str


class ComputerSchemaIn(BaseModel):
    serial: str
