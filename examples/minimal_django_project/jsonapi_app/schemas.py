from typing import Annotated

from pydantic import BaseModel

from django_ninja_jsonapi.types_metadata import RelationshipInfo


class CustomerRefSchema(BaseModel):
    id: int
    name: str
    email: str


class ComputerSchema(BaseModel):
    id: int
    serial: str
    owner: Annotated[
        CustomerRefSchema | None,
        RelationshipInfo(resource_type="customer"),
    ] = None


class CustomerSchema(BaseModel):
    id: int
    name: str
    email: str
    computers: Annotated[
        list[ComputerSchema],
        RelationshipInfo(resource_type="computer", many=True),
    ] = []


class CustomerSchemaIn(BaseModel):
    name: str
    email: str


class ComputerSchemaIn(BaseModel):
    serial: str
