import asyncio
import pathlib

from fast_grpc import FastGRPC, FastGRPCService, grpc_method
from pydantic import BaseModel


class HelloRequest(BaseModel):
    name: str


class HelloResponse(BaseModel):
    text: str | None = None
    meta: dict[str, str] = {}


class Greeter(FastGRPCService):
    name = "CustomGreeter"
    proto_path = pathlib.Path(__file__).parent
    grpc_path = pathlib.Path(__file__).parent

    def __init__(self, cancel_message: str):
        self.cancel_message = cancel_message

        super().__init__()  # It is necessary

    @grpc_method("SayHello", request_model=HelloRequest, response_model=HelloResponse)
    async def say_hello(self, request, context):
        if request.name == "Oleg":
            await context.abort(code=400, details=self.cancel_message)
        return HelloResponse(
            text=f"Hello, {request.name}!",
            meta={"Service": "Greeter"},
        )


app = FastGRPC(
    Greeter(cancel_message="We do not serve Olegs"),
    port=50051,
    reflection=True,
)

loop = asyncio.get_event_loop()
loop.run_until_complete(app.run_async())
loop.close()
