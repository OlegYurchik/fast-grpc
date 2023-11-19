import inspect
import pathlib
import sys
from typing import Any, Callable, Type

from pydantic import BaseModel

from . import proto


class grpc_method:
    def __init__(
            self,
            name: str | None = None,
            request_model: Type[BaseModel] | None = None,
            response_model: Type[BaseModel] | None = None,
            disable: bool = False,
    ):
        self._name = name
        self._request_model = request_model
        self._response_model = response_model
        self._disable = disable

    def __call__(self, function: Callable):
        async def wrapper(self, request, context):
            request_model = wrapper._grpc_method_request_model
            response_model = wrapper._grpc_method_response_model

            request = request_model.model_validate(request, from_attributes=True)

            args = {"self": self, "request": request}
            if "context" in signature.parameters:
                args["context"] = context

            response = await function(**args)

            grpc_model = getattr(self.pb2, response_model.__name__)
            return grpc_model(**response.model_dump(mode="json"))


        signature = inspect.signature(function)
        wrapper._grpc_method_enabled = not self._disable
        wrapper._grpc_method_name = self._name or function.__name__
        wrapper._grpc_method_request_model = (
            self._request_model or self.get_request_model_from_signature(signature)
        )
        wrapper._grpc_method_response_model = (
            self._response_model or self.get_response_model_from_signature(signature)
        )

        return wrapper

    @staticmethod
    def get_request_model_from_signature(signature) -> Type[BaseModel]:
        if "request" not in signature.parameters:
            raise TypeError("GRPC method should have 'request' parameter")
        request_parameter = signature.parameters["request"]
        if not issubclass(request_parameter.annotation, BaseModel):
            raise TypeError("GRPC method parameter 'request' should be pydantic model")
        return request_parameter.annotation

    @staticmethod
    def get_response_model_from_signature(signature) -> Type[BaseModel]:
        if not issubclass(signature.return_annotation, BaseModel):
            raise TypeError("GRPC method should have pydantic model in return annotation")
        return signature.return_annotation


class FastGRPCService:
    _methods: dict[str, Callable] = {}

    def __init__(
            self,
            name: str | None = None,
            proto_path: pathlib.Path = pathlib.Path.cwd(),
            grpc_path: pathlib.Path = pathlib.Path.cwd(),
    ):
        self._name = name or self.__class__.__name__
        self._proto_path = proto_path
        self._grpc_path = grpc_path
        self._pb2 = None
        self._pb2_grpc = None
        self._methods = {}

        self._setup()

    @property
    def name(self) -> str:
        return self._name

    @property
    def proto_path(self) -> pathlib.Path:
        return self._proto_path

    @property
    def grpc_path(self) -> pathlib.Path:
        return self._grpc_path

    @property
    def pb2(self):
        return self._pb2

    @property
    def pb2_grpc(self):
        return self._pb2_grpc

    def __getattribute__(self, __name: str) -> Any:
        methods = object.__getattribute__(self, "_methods")
        if __name in methods:
            return methods[__name]
        return object.__getattribute__(self, __name)

    def get_service_name(self) -> str:
        return self._pb2.DESCRIPTOR.services_by_name[self.name].full_name

    def _gather_methods(self) -> proto.Service:
        self._methods.clear()
        methods = {}
        messages = {}
        for attribute_name in dir(self):
            attribute = getattr(self, attribute_name)
            if not getattr(attribute, "_grpc_method_enabled", False):
                continue

            method_name = attribute._grpc_method_name
            request_message = proto.get_message_from_model(attribute._grpc_method_request_model)
            response_message = proto.get_message_from_model(attribute._grpc_method_response_model) 

            self._methods[method_name] = attribute

            methods[method_name] = proto.Method(
                name=method_name,
                request=request_message,
                response=response_message,
            )
            messages[request_message.name] = request_message
            messages[response_message.name] = response_message

        return proto.Service(name=self.name, methods=methods, messages=messages)

    def _setup(self):
        service = self._gather_methods()
        proto.render_proto(service=service, proto_path=self.proto_path)
        proto.compile_proto(service=service, proto_path=self.proto_path, grpc_path=self.grpc_path)
        proto.delete_proto(service=service, proto_path=self.proto_path)

        grpc_path = str(self._grpc_path)
        if grpc_path not in sys.path:
            sys.path.append(grpc_path)
        self._pb2 = __import__(f"{service.name.lower()}_pb2")
        self._pb2_grpc = __import__(f"{service.name.lower()}_pb2_grpc")
