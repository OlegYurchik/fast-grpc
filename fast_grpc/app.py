import asyncio

from grpc.aio import server
from grpc_reflection.v1alpha import reflection as grpc_reflection

from .service import FastGRPCService


class FastGRPC:
    """FastGRPC server application.

    Args:
        *services (:obj:`list` of :obj:`FastGRPCService`): list of services.
        port (int): port for listen requests. Defaults to 50051.
        reflection (bool): flag for enable server reflection. Defaults to False.
    """

    def __init__(
            self,
            *services: FastGRPCService,
            loop: asyncio.AbstractEventLoop = asyncio.get_event_loop(),
            port: int = 50051,
            reflection: bool = False,
    ):
        self._loop = loop
        self._server = server()
        self._server.add_insecure_port(f"[::]:{port}")

        for service in services:
            self.add_service(service)

        if reflection:
            service_names = [service.get_service_name() for service in services]
            service_names.append(grpc_reflection.SERVICE_NAME)
            grpc_reflection.enable_server_reflection(service_names, self._server)

    def add_service(self, service: FastGRPCService):
        """Add service.

        Args:
            service(:obj:`FastGRPCService`): service.
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
        """Run server."""

        await self._server.start()
        await self._server.wait_for_termination()
