# Fast-gRPC

![Integration](https://github.com/OlegYurchik/fast-grpc/actions/workflows/integration.yaml/badge.svg)
![Documentation](https://app.readthedocs.org/projects/fast-grpc/badge/?version=latest)

Fast-gRPC it is simple and easy to use Python gRPC framework.

## Installation

```shell
pip install py-fast-grpc
```

## Quick Start

```python
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


app = FastGRPC(Greeter())
app.run()
```

## TODO

* Add documentation
* Add middlewares (interceptors) to `FastGRPC` class (for all services)
* Add TLS support
* Move to `uv`
