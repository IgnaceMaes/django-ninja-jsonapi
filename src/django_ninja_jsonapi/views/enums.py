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
    def real_operations(include_delete_list: bool = False) -> list[Operation]:
        operations = [operation for operation in Operation if operation != Operation.ALL]
        if include_delete_list:
            return operations

        return [operation for operation in operations if operation != Operation.DELETE_LIST]

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
