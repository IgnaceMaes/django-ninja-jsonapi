from typing import Annotated

from pydantic import BaseModel

from django_ninja_jsonapi.types_metadata import RelationshipInfo


class ComputerSchema(BaseModel):
    id: int
    serial: str


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
