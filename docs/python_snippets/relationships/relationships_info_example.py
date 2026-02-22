from typing import Annotated, Optional

from pydantic import BaseModel

from django_ninja_jsonapi.types_metadata import RelationshipInfo


class UserBioSchema(BaseModel):
    id: int
    birth_city: str


class ComputerSchema(BaseModel):
    id: int
    serial: str


class UserSchema(BaseModel):
    id: int
    name: str
    bio: Annotated[
        Optional[UserBioSchema],
        RelationshipInfo(resource_type="user_bio", many=False),
    ] = None
    computers: Annotated[
        list[ComputerSchema],
        RelationshipInfo(resource_type="computer", many=True),
    ] = []
