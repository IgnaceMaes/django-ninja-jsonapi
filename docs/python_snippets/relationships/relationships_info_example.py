from typing import Annotated, Optional

from pydantic import BaseModel

from django_ninja_jsonapi.types_metadata import RelationshipInfo


class CustomerBioSchema(BaseModel):
    id: int
    birth_city: str


class ComputerSchema(BaseModel):
    id: int
    serial: str


class CustomerSchema(BaseModel):
    id: int
    name: str
    bio: Annotated[
        Optional[CustomerBioSchema],
        RelationshipInfo(resource_type="customer_bio", many=False),
    ] = None
    computers: Annotated[
        list[ComputerSchema],
        RelationshipInfo(resource_type="computer", many=True),
    ] = []
