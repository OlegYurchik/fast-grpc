import pydantic

from fast_grpc import FastGRPCService, grpc_method


class PyTestRequest(pydantic.BaseModel):
    message: str


class PyTestResponse(pydantic.BaseModel):
    message: str


class PyTestService(FastGRPCService):
    @grpc_method()
    async def test(self, request: PyTestRequest, context) -> PyTestResponse:
        return PyTestResponse(message=request.message)

    @grpc_method(name="test_2", request_model=PyTestRequest, response_model=PyTestResponse)
    async def second_test(self, request):
        return PyTestResponse(message=request.message)


service_content_first = """
syntax = "proto3";
package pytestservice;

service PyTestService {
    rpc test_2(PyTestRequest) returns (PyTestResponse) {}
    rpc test(PyTestRequest) returns (PyTestResponse) {}
}

message PyTestResponse {
    string message = 1;
}

message PyTestRequest {
    string message = 1;
}
"""
service_content_second = """
syntax = "proto3";
package pytestservice;

service PyTestService {
    rpc test_2(PyTestRequest) returns (PyTestResponse) {}
    rpc test(PyTestRequest) returns (PyTestResponse) {}
}

message PyTestRequest {
    string message = 1;
}

message PyTestResponse {
    string message = 1;
}
"""


def test_get_proto():
    service = PyTestService()
    expected_variants = [
        service_content_first.strip(),
        service_content_second.strip(),
    ]

    assert service.get_proto().strip() in expected_variants
