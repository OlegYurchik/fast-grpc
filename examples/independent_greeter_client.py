import asyncio

from pydantic import BaseModel

from fast_grpc import FastGRPC, FastGRPCService, grpc_method


class HelloRequest(BaseModel):
    name: str


class HelloResponse(BaseModel):
    text: str


class GreeterInterface(FastGRPCService):
    name = "Greeter"

    @grpc_method
    async def say_hello(self, request: HelloRequest) -> HelloResponse:
        raise NotImplementedError


class Greeter(GreeterInterface):
    @grpc_method
    async def say_hello(self, request: HelloRequest) -> HelloResponse:
        return HelloResponse(text=f"Hello, {request.name}")


async def main():
    loop = asyncio.get_event_loop()
    app = FastGRPC(Greeter(), reflection=True)

    print("Running Greeter on port 50051...")
    app_task = loop.create_task(app.run_async())

    print("Waiting 5 seconds...")
    await asyncio.sleep(5)

    client = GreeterInterface.Client(host="127.0.0.1", port=50051)
    request = HelloRequest(name="Oleg")
    print("Calling Greeting say_hello...")
    response = await client.say_hello(request=request)  # pylint: disable=no-member
    print("Response:", response.model_dump(mode="json"))

    app_task.cancel()
    try:
        await app_task
    except asyncio.CancelledError:
        pass


if __name__ == "__main__":
    asyncio.run(main())
