import logging

from pydantic import BaseModel

from fast_grpc import FastGRPC, FastGRPCMiddleware, FastGRPCService, grpc_method


class HelloRequest(BaseModel):
    name: str


class HelloResponse(BaseModel):
    text: str


class LogMiddleware(FastGRPCMiddleware):
    def __init__(self, logger: logging.Logger):
        self.logger = logger

    async def __call__(self, next_call, request, context):
        self.logger.info("Get request")
        response = await next_call(request, context)
        self.logger.info("Build response")
        return response


async def replacement_middleware(next_call, request, context):
    return HelloResponse(text="Good bye!")


class Greeter(FastGRPCService):
    middlewares = [LogMiddleware(logger=logging.getLogger(__name__))]

    @grpc_method(middlewares=[replacement_middleware])
    async def say_hello(self, request: HelloRequest) -> HelloResponse:
        return HelloResponse(text=f"Hello, {request.name}!")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = FastGRPC(Greeter(), reflection=True)
    app.run()
