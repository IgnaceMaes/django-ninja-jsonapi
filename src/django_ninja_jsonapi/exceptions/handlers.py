from django.http import HttpRequest, JsonResponse

from django_ninja_jsonapi.exceptions import HTTPException


def base_exception_handler(request: HttpRequest, exc: HTTPException):
    return JsonResponse(
        status=exc.status_code,
        data={"errors": [exc.as_dict]},
    )
