import functools
import inspect
import pathlib
import sys
from typing import Any, Callable, Type

import grpc
from google.protobuf.json_format import MessageToDict, ParseDict
from pydantic import BaseModel

from . import proto
from .middleware import FastGRPCMiddleware


class grpc_method:
    def __init__(
            self,
            name: str | None = None,
            request_model: Type[BaseModel] | None = None,
            response_model: Type[BaseModel] | None = None,
            middlewares: list[FastGRPCMiddleware | Callable] | None = None,
            disable: bool = False,
    ):
        self._name = name
        self._request_model = request_model
        self._response_model = response_model
        self._middlewares = middlewares
        self._disable = disable

    def __call__(self, function: Callable):
        async def wrapper(self, request, context):
            request_model = wrapper._grpc_method_request_model
            response_model = wrapper._grpc_method_response_model
            middlewares = self.middlewares + wrapper._grpc_method_middlewares

            request = request_model.model_validate(request, from_attributes=True)

            async def _function(request, context):
                args = {"request": request}
                if "context" in signature.parameters:
                    args["context"] = context

                return await function(**args)

            for middleware in middlewares[::-1]:
                _function = functools.partial(middleware, _function)

            response = await _function(request, context)

            grpc_model = getattr(self.pb2, response_model.__name__)
            return ParseDict(
                response.model_dump(mode="json"),
                grpc_model(),
                ignore_unknown_fields=True,
            )

        signature = inspect.signature(function)
        wrapper.__name__ = function.__name__
        wrapper._grpc_method_name = self._name or function.__name__
        wrapper._grpc_method_request_model = (
            self._request_model or self.get_request_model_from_signature(signature)
        )
        wrapper._grpc_method_response_model = (
            self._response_model or self.get_response_model_from_signature(signature)
        )
        wrapper._grpc_method_middlewares = self._middlewares
        wrapper._grpc_method_enabled = not self._disable

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


class FastGRPCServiceMeta(type):
    def __init__(cls, name: str, bases: tuple[type], attributes: dict[str, Any]):
        super().__init__(name, bases, attributes)

        if not attributes.get("is_proxy", False):
            cls.name = attributes.pop("name", name)
            cls.proto_path = pathlib.Path(attributes.pop("proto_path", pathlib.Path.cwd()))
            cls.grpc_path = pathlib.Path(attributes.pop("grpc_path", pathlib.Path.cwd()))
            cls.save_proto = attributes.pop("save_proto", False)
            cls.middlewares = attributes.pop("middlewares", ())
            cls._methods = {}

            cls._setup()

    def _setup(cls):
        service = cls.build_proto_service()
        try:
            content = proto.render_proto(service=service)
            proto.write_proto(service=service, proto_path=cls.proto_path, content=content)
            proto.compile_proto(service=service, proto_path=cls.proto_path,
                                grpc_path=cls.grpc_path)
        finally:
            if not cls.save_proto:
                proto.delete_proto(service=service, proto_path=cls.proto_path)

        grpc_path = str(cls.grpc_path)
        if grpc_path not in sys.path:
            sys.path.append(grpc_path)
        cls.pb2 = __import__(f"{service.name.lower()}_pb2")
        cls.pb2_grpc = __import__(f"{service.name.lower()}_pb2_grpc")
        cls.Client = cls.get_client()

    def build_proto_service(cls) -> proto.Service:
        cls._methods.clear()
        methods = {}
        messages = {}
        models = set()
        for attribute_name in dir(cls):
            attribute = getattr(cls, attribute_name)
            if not getattr(attribute, "_grpc_method_enabled", False):
                continue

            method_name = attribute._grpc_method_name
            models |= proto.gather_models(attribute._grpc_method_request_model)
            models |= proto.gather_models(attribute._grpc_method_response_model)
            request_message = proto.get_message_from_model(attribute._grpc_method_request_model)
            response_message = proto.get_message_from_model(attribute._grpc_method_response_model) 

            cls._methods[method_name] = attribute

            methods[method_name] = proto.Method(
                name=method_name,
                request=request_message,
                response=response_message,
            )
            for model in models:
                message = proto.get_message_from_model(model)
                messages[message.name] = message

        return proto.Service(name=cls.name, methods=methods, messages=messages)

    def get_client(cls) -> type:
        class_name = f"{cls.name}Client"
        attributes = {}
        for grpc_method_name, method in cls._methods.items():
            request_message_class = getattr(cls.pb2, method._grpc_method_request_model.__name__)
            response_message_class = method._grpc_method_response_model

            async def wrapper(
                    self,
                    request,
                    _grpc_method_name=grpc_method_name,
                    _request_message_class=request_message_class,
                    _response_message_class=response_message_class,
            ):
                grpc_method = getattr(self._stub, _grpc_method_name)
                grpc_request = ParseDict(request.model_dump(mode="json"), _request_message_class())
                response = await grpc_method(request=grpc_request)
                response_dict = MessageToDict(response, preserving_proto_field_name=True)
                return _response_message_class.model_validate(response_dict)

            attributes[method.__name__] = wrapper

        def __init__(self, host: str, port: int):
            channel = grpc.aio.insecure_channel(f"{host}:{port}")
            self._stub = getattr(cls.pb2_grpc, f"{cls.name}Stub")(channel)

        attributes["__init__"] = __init__

        return type(class_name, (), attributes)

    
class FastGRPCService(metaclass=FastGRPCServiceMeta):
    is_proxy: bool = True

    def __getattribute__(self, __name: str) -> Any:
        methods = object.__getattribute__(self, "_methods")
        if __name in methods:
            return methods[__name].__get__(self, self.__class__)
        return object.__getattribute__(self, __name)

    def get_service_name(self) -> str:
        return self.pb2.DESCRIPTOR.services_by_name[self.name].full_name

    @classmethod
    def get_proto(cls) -> str:
        service = cls.build_proto_service()
        content = proto.render_proto(service=service)
        return content
