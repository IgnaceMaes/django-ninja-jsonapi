from typing import ClassVar

from pydantic import BaseModel, ConfigDict

from django_ninja_jsonapi import JsonApiMeta


class ComputerSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    serial: str

    jsonapi_meta: ClassVar[JsonApiMeta] = JsonApiMeta(resource_type="computers")


class CustomerSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    computers: list[ComputerSchema] = []

    jsonapi_meta: ClassVar[JsonApiMeta] = JsonApiMeta(resource_type="customers")


class CustomerSchemaIn(BaseModel):
    name: str
    email: str


class ComputerSchemaIn(BaseModel):
    serial: str
