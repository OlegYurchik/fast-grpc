import asyncio

from grpc.aio import server
from grpc_reflection.v1alpha import reflection as grpc_reflection

from .service import FastGRPCService


class FastGRPC:
    def __init__(self, *services: FastGRPCService, port: int = 50051, reflection: bool = False):
        self._server = server()
        self._server.add_insecure_port(f"[::]:{port}")

        for service in services:
            self.add_service(service)

        if reflection:
            service_names = [svc.get_service_name() for svc in services]
            service_names.append(grpc_reflection.SERVICE_NAME)
            grpc_reflection.enable_server_reflection(service_names, self._server)

    def add_service(self, service: FastGRPCService):
        register_function = getattr(service.pb2_grpc, f"add_{service.name}Servicer_to_server")
        register_function(service, self._server)

    def run(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.run_async())
        loop.close()

    async def run_async(self):
        await self._server.start()
        await self._server.wait_for_termination()
