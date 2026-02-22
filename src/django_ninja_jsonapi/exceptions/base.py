"""Collection of useful http error for the Api."""

from typing import Any, Optional

from pydantic import Field
from pydantic.main import BaseModel


class ExceptionSourceSchema(BaseModel):
    """Source exception schema."""

    parameter: Optional[str] = None
    pointer: Optional[str] = None


class ExceptionSchema(BaseModel):
    """Exception schema."""

    status: str
    source: Optional[ExceptionSourceSchema] = None
    title: str
    detail: Any


class ExceptionResponseSchema(BaseModel):
    """Exception response schema."""

    errors: list[ExceptionSchema]
    jsonapi: dict[str, str] = Field(default={"version": "1.0"})
