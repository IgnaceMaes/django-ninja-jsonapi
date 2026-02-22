from __future__ import annotations

from enum import Enum, auto


class Operation(str, Enum):
    ALL = auto()
    CREATE = auto()
    DELETE = auto()
    DELETE_LIST = auto()
    GET = auto()
    GET_LIST = auto()
    UPDATE = auto()

    @staticmethod
    def real_operations() -> list[Operation]:
        return list(filter(lambda op: op != Operation.ALL, Operation))

    def http_method(self) -> str:
        if self == Operation.ALL:
            msg = "HTTP method is not defined for 'ALL' operation."
            raise Exception(msg)

        operation_to_http_method = {
            Operation.GET: "GET",
            Operation.GET_LIST: "GET",
            Operation.UPDATE: "PATCH",
            Operation.CREATE: "POST",
            Operation.DELETE: "DELETE",
            Operation.DELETE_LIST: "DELETE",
        }
        return operation_to_http_method[self]
