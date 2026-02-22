from functools import wraps
from http import HTTPStatus

from pydantic import ValidationError

from django_ninja_jsonapi.exceptions import HTTPException


def handle_validation_error(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValidationError as ex:
            raise HTTPException(
                status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
                detail=ex.errors(),
            ) from ex

    return wrapper
