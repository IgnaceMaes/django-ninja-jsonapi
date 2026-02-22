from django_ninja_jsonapi.views.enums import Operation
from django_ninja_jsonapi.views.schemas import OperationConfig, RelationshipRequestInfo

__all__ = [
    "Operation",
    "OperationConfig",
    "RelationshipRequestInfo",
    "ViewBase",
]


def __getattr__(name: str):
    if name == "ViewBase":
        from django_ninja_jsonapi.views.view_base import ViewBase

        return ViewBase

    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
