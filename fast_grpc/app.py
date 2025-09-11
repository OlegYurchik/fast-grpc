import asyncio
import functools
from typing import Callable

import grpc
from grpc.aio import server
from grpc_interceptor.server import AsyncServerInterceptor
from grpc_reflection.v1alpha import reflection as grpc_reflection

from .middleware import FastGRPCMiddleware
from .service import FastGRPCService


class _FastGRPCInterceptor(AsyncServerInterceptor):
    def __init__(
            self,
            middlewares: tuple[FastGRPCService | Callable] = (),
    ):
        self._middlewares = middlewares

    async def intercept(
            self,
            method: Callable,
            request_or_iterator,
            context: grpc.ServicerContext,
            method_name: str,
    ):
        async def wrapper(request, context):
            coroutine_or_iterator = method(request_or_iterator, context)
            if hasattr(coroutine_or_iterator, "__aiter__"):
                return coroutine_or_iterator
            return await coroutine_or_iterator

        for middleware in self._middlewares[::-1]:
            wrapper = functools.partial(middleware, wrapper)
        return await wrapper(request_or_iterator, context)


class FastGRPC:
    """Server application.

    Args:
        *services (tuple[FastGRPCService]): Tuple of Fast-gRPC services.
        loop (asyncio.AbstractEventLoop): Async event loop for running server.
        port (int): Port for listen requests.
        reflection (bool): Flag for enable/disable server gRPC reflection.

    Example:
        ```python
        from fast_grpc import FastGRPC, FastGRPCService, grpc_method

        class ExampleService(FastGRPCService):
            ...

        app = FastGRPC(ExampleService())
        app.run()
        ```
    """

    def __init__(
            self,
            *services: FastGRPCService,
            loop: asyncio.AbstractEventLoop = asyncio.get_event_loop(),
            port: int = 50051,
            reflection: bool = False,
            middlewares: tuple[FastGRPCMiddleware | Callable] = (),
    ):
        self._loop = loop
        self._server = server(
            interceptors=[_FastGRPCInterceptor(middlewares=middlewares)],
        )
        self._server.add_insecure_port(f"[::]:{port}")

        for service in services:
            self.add_service(service)

        if reflection:
            service_names = [service.get_service_name() for service in services]
            service_names.append(grpc_reflection.SERVICE_NAME)
            grpc_reflection.enable_server_reflection(service_names, self._server)

    def add_service(self, service: FastGRPCService):
        """Add service to server.

        Args:
            service (FastGRPCService): gRPC service.

        Example:
            ```python
            app = FastGRPC()
            app.add_service(ExampleService())
            ```
        """

        register_function = getattr(service.pb2_grpc, f"add_{service.name}Servicer_to_server")
        register_function(service, self._server)

    def run(self):
        """Run server."""

        try:
            self._loop.run_until_complete(self.run_async())
        finally:
            self._loop.close()

    async def run_async(self):
        """Run server.
        
        Example:
            ```python
            app = FastGRPC()
            await app.run_async()
            ```
        """

        await self._server.start()
        await self._server.wait_for_termination()
