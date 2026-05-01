from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpRequest, JsonResponse
from pydantic import ValidationError

from django_ninja_jsonapi.exceptions import HTTPException
from django_ninja_jsonapi.renderers import JSONAPI_MEDIA_TYPE


def base_exception_handler(request: HttpRequest, exc: HTTPException):
    return JsonResponse(
        status=exc.status_code,
        data={"errors": [exc.as_dict]},
        content_type=JSONAPI_MEDIA_TYPE,
    )


def object_does_not_exist_handler(request: HttpRequest, exc: ObjectDoesNotExist):
    detail = str(exc) if str(exc) else "Resource not found."
    return JsonResponse(
        status=404,
        data={
            "errors": [
                {
                    "status": "404",
                    "title": "Not Found",
                    "detail": detail,
                    "source": {"pointer": ""},
                }
            ]
        },
        content_type=JSONAPI_MEDIA_TYPE,
    )


def pydantic_validation_exception_handler(request: HttpRequest, exc: ValidationError):
    errors = []
    for error in exc.errors():
        pointer = "/data"
        loc = error.get("loc", ())
        if loc:
            pointer = "/data/" + "/".join(str(part) for part in loc)
        errors.append(
            {
                "status": "422",
                "title": "Validation Error",
                "detail": error.get("msg", str(error)),
                "source": {"pointer": pointer},
            }
        )
    return JsonResponse(
        status=422,
        data={"errors": errors},
        content_type=JSONAPI_MEDIA_TYPE,
    )
