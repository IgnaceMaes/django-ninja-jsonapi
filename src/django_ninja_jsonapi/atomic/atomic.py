from http import HTTPStatus
from typing import Optional, Type

from django.http import HttpRequest, HttpResponse
from ninja import Router

from django_ninja_jsonapi.atomic.atomic_handler import AtomicViewHandler
from django_ninja_jsonapi.atomic.schemas import AtomicOperationRequest, AtomicResultResponse


class AtomicOperations:
    atomic_handler: Type[AtomicViewHandler] = AtomicViewHandler

    def __init__(
        self,
        url_path: str = "/operations",
        router: Optional[Router] = None,
    ):
        self.router = router or Router(tags=["Atomic Operations"])
        self.url_path = url_path
        self._register_view()

    async def view_atomic(
        self,
        request: HttpRequest,
        operations_request: AtomicOperationRequest,
    ):
        atomic_handler = self.atomic_handler(
            request=request,
            operations_request=operations_request,
        )
        result = await atomic_handler.handle()
        if result:
            return result
        return HttpResponse(status=HTTPStatus.NO_CONTENT)

    def _register_view(self) -> None:
        async def endpoint(request: HttpRequest, operations_request: AtomicOperationRequest):
            return await self.view_atomic(
                request=request,
                operations_request=operations_request,
            )

        self.router.post(
            self.url_path,
            response=AtomicResultResponse,
            summary="Atomic operations",
            description="""[https://jsonapi.org/ext/atomic/](https://jsonapi.org/ext/atomic/)""",
        )(endpoint)
