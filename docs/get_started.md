# Get Started

## Installation
```bash
pip install py-fast-grpc
```

## 1. Define Service
Create service:
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


app = FastGRPC(Greeter(), reflection=True)
app.run()
```
