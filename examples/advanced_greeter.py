# import sys
# breakpoint()

import pathlib

from pydantic import BaseModel

from fast_grpc import FastGRPC, FastGRPCService, StatusCode, grpc_method


class HelloRequest(BaseModel):
    name: str


class HelloMetaResponse(BaseModel):
    key: str
    value: str


class HelloResponse(BaseModel):
    text: str | None = None
    meta: dict[str, HelloMetaResponse] = {}


class ByeRequest(BaseModel):
    name: str


class ByeResponse(BaseModel):
    text: str | None = None


class Greeter(FastGRPCService):
    is_proxy = False
    disabled = False

    name = "AdvancedGreeter"
    package_name = "fast_grpc.examples.advanced_greeter"
    proto_path = pathlib.Path(__file__).parent
    grpc_path = pathlib.Path(__file__).parent
    save_proto = False
    middlewares = []

    def __init__(self, cancel_message: str):
        self.cancel_message = cancel_message

    @grpc_method(name="sayHello", request_model=HelloRequest, response_model=HelloResponse)
    async def say_hello(self, request, context):
        if request.name == "Oleg":
            await context.abort(code=StatusCode.PERMISSION_DENIED, details=self.cancel_message)
        return HelloResponse(
            text=f"Hello, {request.name}!",
            meta={"response": HelloMetaResponse(key="service", value="Greeter")},
        )

    @grpc_method(disable=True)
    async def say_bye(self, request: ByeRequest) -> ByeResponse:
        raise NotImplementedError


if __name__ == "__main__":
    service = Greeter(cancel_message="We do not serve Olegs")
    app = FastGRPC(service, port=50051, reflection=True)

    print("Protobuf file content for service Greeter")
    print(service.get_proto())  # Print .proto file content

    print("Running Greeter on port 50051...")
    app.run()
