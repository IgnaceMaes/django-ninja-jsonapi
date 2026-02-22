from __future__ import annotations

import logging
from collections import defaultdict
from contextvars import ContextVar
from functools import wraps
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Optional, TypedDict, Union

from django.http import HttpRequest
from pydantic import ValidationError

from django_ninja_jsonapi.atomic.prepared_atomic_operation import LocalIdsType, OperationBase
from django_ninja_jsonapi.atomic.schemas import AtomicOperation, AtomicOperationRequest, AtomicResultResponse
from django_ninja_jsonapi.exceptions import HTTPException
from django_ninja_jsonapi.storages.schemas_storage import schemas_storage

if TYPE_CHECKING:
    from django_ninja_jsonapi.data_layers.base import BaseDataLayer
    from django_ninja_jsonapi.data_typing import TypeSchema

log = logging.getLogger(__name__)
AtomicResponseDict = TypedDict("AtomicResponseDict", {"atomic:results": list[Any]})
current_atomic_operation: ContextVar[OperationBase] = ContextVar("current_atomic_operation")


def catch_exc_on_operation_handle(func: Callable[..., Awaitable]):
    @wraps(func)
    async def wrapper(*a, operation: OperationBase, **kw):
        try:
            return await func(*a, operation=operation, **kw)
        except (ValidationError, ValueError) as ex:
            log.exception(
                "Validation error on atomic action ref=%s, data=%s",
                operation.ref,
                operation.data,
            )
            errors_details = {
                "message": f"Validation error on operation {operation.op_type}",
                "ref": operation.ref,
                "data": operation.data.model_dump(),
            }
            if isinstance(ex, ValidationError):
                errors_details.update(errors=ex.errors())
            elif isinstance(ex, ValueError):
                errors_details.update(error=f"{ex}")
            else:
                raise
            # TODO: json:api exception
            raise HTTPException(
                status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
                detail=errors_details,
            ) from ex

    return wrapper


class AtomicViewHandler:
    def __init__(
        self,
        request: HttpRequest,
        operations_request: AtomicOperationRequest,
    ):
        self.request = request
        self.operations_request = operations_request
        self.local_ids_cache: LocalIdsType = defaultdict(dict)

    async def prepare_one_operation(self, operation: AtomicOperation):
        """
        Prepare one atomic operation

        :param operation:
        :return:
        """
        resource_type = (operation.ref and operation.ref.type) or (operation.data and operation.data.type)
        if not schemas_storage.has_resource(resource_type):
            msg = f"Unknown resource type {resource_type!r}."
            raise ValueError(msg)

        return OperationBase.prepare(
            action=operation.op,
            request=self.request,
            resource_type=resource_type,
            ref=operation.ref,
            data=operation.data,
        )

    async def prepare_operations(self) -> list[OperationBase]:
        prepared_operations: list[OperationBase] = []

        for operation in self.operations_request.operations:
            one_operation = await self.prepare_one_operation(operation)
            prepared_operations.append(one_operation)

        return prepared_operations

    @catch_exc_on_operation_handle
    async def process_one_operation(
        self,
        dl: BaseDataLayer,
        operation: OperationBase,
    ):
        operation.update_relationships_with_lid(local_ids=self.local_ids_cache)
        return await operation.handle(dl=dl)

    async def process_next_operation(
        self,
        operation: OperationBase,
        previous_dl: Optional[BaseDataLayer],
    ) -> tuple[Optional[TypeSchema], BaseDataLayer]:
        dl = await operation.get_data_layer()
        await dl.atomic_start(
            previous_dl=previous_dl,
        )
        try:
            response = await self.process_one_operation(
                dl=dl,
                operation=operation,
            )
        except HTTPException as ex:
            await dl.atomic_end(
                success=False,
                exception=ex,
            )
            raise ex

        return response, dl

    async def handle(self) -> Union[AtomicResponseDict, AtomicResultResponse, None]:
        prepared_operations = await self.prepare_operations()
        results = []
        only_empty_responses = True
        success = True
        previous_dl: Optional[BaseDataLayer] = None
        for operation in prepared_operations:
            # set context var
            ctx_var_token = current_atomic_operation.set(operation)

            response, dl = await self.process_next_operation(operation, previous_dl)
            previous_dl = dl

            # response.data.id
            if not response:
                # https://jsonapi.org/ext/atomic/#result-objects
                # An empty result object ({}) is acceptable
                # for operations that are not required to return data.
                results.append({})
                continue
            only_empty_responses = False

            data = response["data"]
            results.append(
                {"data": data},
            )

            if operation.data.lid and data:
                self.local_ids_cache[operation.data.type][operation.data.lid] = data["id"]

            # reset context var
            current_atomic_operation.reset(ctx_var_token)

        if previous_dl:
            await previous_dl.atomic_end(success=success)

        if not only_empty_responses:
            return {"atomic:results": results}

        """
        if all results are empty,
        the server MAY respond with 204 No Content and no document.
        """
