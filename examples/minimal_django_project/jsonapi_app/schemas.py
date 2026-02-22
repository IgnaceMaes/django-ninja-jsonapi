from pydantic import BaseModel


class UserSchema(BaseModel):
    id: int
    name: str
    email: str


class ComputerSchema(BaseModel):
    id: int
    serial: str
    owner_id: int | None = None


class UserSchemaIn(BaseModel):
    name: str
    email: str


class ComputerSchemaIn(BaseModel):
    serial: str
