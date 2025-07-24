import asyncio
import pathlib

from fast_grpc import FastGRPC, FastGRPCService, grpc_method
from pydantic import BaseModel


class Meta(BaseModel):
    key: str
    value: str | None


class ExampleRequest(BaseModel):
    request: str


class ExampleResponse(BaseModel):
    result: bool
    meta: list[Meta]


class ExampleService(FastGRPCService):
    name = "Example"
    package_name = "service.from.proto"

    @grpc_method
    async def test(self, request: ExampleRequest) -> ExampleResponse:
        return ExampleResponse(
            result=True,
            meta=[Meta(key="request", value=request.request)],
        )


async def main():
    loop = asyncio.get_event_loop()
    app = FastGRPC(ExampleService(), loop=loop, reflection=True)
    print("Running Example on port 50051...")
    app_task = loop.create_task(app.run_async())
    print("Waiting 5 seconds...")
    await asyncio.sleep(5)

    proto_file = pathlib.Path(__file__).parent / "service_from_proto.proto"
    ImportedExampleService = FastGRPCService.from_proto(proto_file=proto_file)
    client = ImportedExampleService.Client(host="127.0.0.1", port=50051)

    print("Calling Example test...")
    request = ExampleRequest(request="avada_kedavra")
    response = await client.test(request=request)
    print("Response:", response.model_dump(mode="json"))

    app_task.cancel()
    try:
        await app_task
    except asyncio.CancelledError:
        pass


if __name__ == "__main__":
    asyncio.run(main())
