from fast_grpc import FastGRPC, FastGRPCService, grpc_method
from pydantic import BaseModel


class HelloRequest(BaseModel):
    name: str


class HelloResponse(BaseModel):
    text: str


class Greeter(FastGRPCService):
    @grpc_method
    async def say_hello(self, request: HelloRequest) -> HelloResponse:
        return HelloResponse(text=f"Hello, {request.name}!")


if __name__ == "__main__":
    app = FastGRPC(Greeter(), reflection=True)

    print("Running Greeter on port 50051...")
    app.run()
