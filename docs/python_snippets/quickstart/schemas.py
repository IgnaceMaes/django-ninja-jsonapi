from typing import Annotated, Optional

from pydantic import BaseModel

from django_ninja_jsonapi.types_metadata import RelationshipInfo


class ComputerSchema(BaseModel):
    id: int
    serial: str
    owner: Annotated[
        Optional["CustomerSchema"],
        RelationshipInfo(resource_type="customer", many=False),
    ] = None


class CustomerSchema(BaseModel):
    id: int
    name: str
    email: str
    computers: Annotated[
        list[ComputerSchema],
        RelationshipInfo(resource_type="computer", many=True),
    ] = []
