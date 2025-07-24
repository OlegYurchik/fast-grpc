# Examples

## Simple Greeter

```{codeinclude} examples/greeter.py
:language: python
```

1. Importing Dependencies

```python
from pydantic import BaseModel
from fast_grpc import FastGRPC, FastGRPCService, grpc_method
```

* **Pydantic's BaseModel**: Used to define strongly-typed data models for requests and responses
* **FastGRPC**: The core application class that manages the gRPC server
* **FastGRPCService**: Base class for gRPC services (must be inherited)
* **grpc_method**: Decorator that registers methods as gRPC endpoints

2. Defining Data Models

```python
class HelloRequest(BaseModel):
    name: str

class HelloResponse(BaseModel):
    text: str
```

* **HelloRequest**: Input model with required name field (string)
* **HelloResponse**: Output model with text field (string)

These models provide automatic validation and serialization

3. Creating the gRPC Service

```python
class Greeter(FastGRPCService):
    @grpc_method
    async def say_hello(self, request: HelloRequest) -> HelloResponse:
        return HelloResponse(text=f"Hello, {request.name}!")
```

* **Inherits from FastGRPCService**: Required for all gRPC services
* **@grpc_method decorator**: Marks say_hello as a gRPC endpoint
* **Type annotations**: Ensure request/response types are strictly enforced
* **Business logic**: Simple greeting generation using request data

4. Server Initialization and Execution

```python
if __name__ == "__main__":
    app = FastGRPC(Greeter(), reflection=True)
    print("Running Greeter on port 50051...")
    app.run()
```

* **FastGRPC()**: Creates the main application instance
* **reflection=True**: Enables gRPC reflection for service discovery
* **app.run()**: Starts the server on default port 50051
