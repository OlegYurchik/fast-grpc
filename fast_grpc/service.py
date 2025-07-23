import functools
import inspect
import pathlib
import sys
import weakref
from typing import Any, Callable, Iterable

import grpc
from google.protobuf.json_format import MessageToDict, ParseDict
from pydantic import BaseModel

from . import proto
from .middleware import FastGRPCMiddleware


class GRPCMethod:
    def __init__(
            self,
            function: Callable,
            name: str | None = None,
            request_model: type[BaseModel] | None = None,
            response_model: type[BaseModel] | None = None,
            middlewares: tuple[FastGRPCMiddleware | Callable] = (),
            enabled: bool = True,
    ):
        self._function = function

        names = (name, function.__name__)
        names = tuple(filter(None, names))
        self._name = names[0]
        self._aliases = tuple(set(names) - {self._name})

        self._request_model = (
            request_model or self._get_request_model_from_function(function=function)
        )
        self._response_model = (
            response_model or self._get_response_model_from_function(function=function)
        )
        self._middlewares = middlewares
        self._is_enabled = enabled

    @property
    def name(self) -> str:
        return self._name

    @property
    def aliases(self) -> tuple[str]:
        return self._aliases

    @property
    def request_model(self) -> type[BaseModel]:
        return self._request_model

    @property
    def response_model(self) -> type[BaseModel]:
        return self._response_model

    @property
    def middlewares(self) -> tuple[FastGRPCMiddleware | Callable]:
        return self._middlewares

    @property
    def is_enabled(self) -> bool:
        return self._is_enabled

    @staticmethod
    def _apply_middlewares_to_function(
            function: Callable,
            service: "FastGRPCService",
            middlewares: tuple[FastGRPCMiddleware | Callable] = (),
    ) -> Callable:
        signature = inspect.signature(function)

        async def wrapper(request, context) -> BaseModel:
            args = {"request": request}
            if "self" in signature.parameters:
                args["self"] = service
            if "context" in signature.parameters:
                args["context"] = context
            return await function(**args)

        for middleware in middlewares[::-1]:
            wrapper = functools.partial(middleware, wrapper)

        return wrapper

    @staticmethod
    def _get_request_model_from_function(function: Callable) -> type[BaseModel]:
        signature = inspect.signature(function)
        if "request" not in signature.parameters:
            raise TypeError("GRPC method should have 'request' parameter")

        request_parameter = signature.parameters["request"]
        if request_parameter.annotation is inspect.Parameter.empty:
            raise TypeError("GRPC method argument 'request' must have pydantic model annotation")
        if not issubclass(request_parameter.annotation, BaseModel):
            raise TypeError("GRPC method parameter 'request' should be pydantic model")

        return request_parameter.annotation

    @staticmethod
    def _get_response_model_from_function(function: Callable) -> type[BaseModel]:
        signature = inspect.signature(function)
        if signature.return_annotation is inspect.Parameter.empty:
            raise TypeError("GRPC method must have pydantic model return annotation")
        if not issubclass(signature.return_annotation, BaseModel):
            raise TypeError("GRPC method should have pydantic model in return annotation")

        return signature.return_annotation

    def __get__(self, instance: object | None, cls: type):
        if instance is None:
            return self
        return functools.partial(self.__call__, instance)

    async def __call__(self, service: "FastGRPCService", request, context):
        function = self._apply_middlewares_to_function(
            function=self._function,
            service=service,
            middlewares=service.middlewares + self._middlewares,
        )
        inner_request = self._request_model.model_validate(request, from_attributes=True)
        response = await function(request=inner_request, context=context)

        grpc_model = getattr(service.pb2, self._response_model.__name__)
        return ParseDict(
            response.model_dump(mode="json"),
            grpc_model(),
            ignore_unknown_fields=True,
        )


def grpc_method(
        function: Callable | None = None,
        /,
        name: str | None = None,
        request_model: type[BaseModel] | None = None,
        response_model: type[BaseModel] | None = None,
        middlewares: Iterable[FastGRPCMiddleware | Callable] = (),
        disable: bool = False,
):
    def decorator(function: Callable) -> GRPCMethod:
        return GRPCMethod(
            function=function,
            name=name,
            request_model=request_model,
            response_model=response_model,
            middlewares=tuple(middlewares),
            enabled=not disable,
        )

    if function is not None:
        return decorator(function=function)
    return decorator


class FastGRPCServiceMeta(type):
    def __init__(cls, name: str, bases: tuple[type], attributes: dict[str, Any]):
        cls.is_enabled = not attributes.get("disabled", False)
        cls.is_proxy = attributes.get("is_proxy", False)
        cls.name = attributes.pop("name", name)
        cls.proto_path = pathlib.Path(attributes.pop("proto_path", pathlib.Path.cwd()))
        cls.grpc_path = pathlib.Path(attributes.pop("grpc_path", pathlib.Path.cwd()))
        cls.save_proto = attributes.pop("save_proto", False)
        cls.middlewares = tuple(attributes.pop("middlewares", ()))

        cls._grpc_methods = cls._gather_grpc_methods()  # pylint: disable=no-value-for-parameter
        cls._proto_service = cls.get_proto_service(
            name=cls.name,
            grpc_methods=cls._grpc_methods,
        )
        if cls.is_enabled and not cls.is_proxy:
            cls.pb2, cls.pb2_grpc = cls.generate_pb2(
                proto_service=cls._proto_service,
                proto_path=cls.proto_path,
                grpc_path=cls.grpc_path,
                save_proto=cls.save_proto,
            )
            cls.Client: type = cls.generate_client(
                name=cls.name,
                grpc_methods=cls._grpc_methods,
                pb2=cls.pb2,
                pb2_grpc=cls.pb2_grpc,
            )
        weakref.finalize(cls, cls.__del__)

        super().__init__(name, bases, attributes)

    def __del__(cls):
        if not cls.is_enabled or cls.is_proxy:
            return

        service_name = cls._proto_service.name.lower()
        pb2_file = cls.grpc_path / f"{service_name}_pb2.py"
        if pb2_file.is_file():
            pb2_file.unlink()
        pb2_grpc_file = cls.grpc_path / f"{service_name}_pb2_grpc.py"
        if pb2_grpc_file.is_file():
            pb2_grpc_file.unlink()

    def _gather_grpc_methods(cls) -> dict[str, GRPCMethod]:
        grpc_methods = {}
        for attribute_name in dir(cls):
            attribute = getattr(cls, attribute_name)
            if not isinstance(attribute, GRPCMethod) or not attribute.is_enabled:
                continue

            grpc_methods[attribute.name] = attribute

        return grpc_methods

    @staticmethod
    def get_proto_service(
            name: str,
            grpc_methods: dict[str, GRPCMethod],
    ) -> proto.Service:
        methods = {}
        messages = {}
        models = set()
        for grpc_method_name, grpc_method in grpc_methods.items():
            models |= proto.gather_models(grpc_method.request_model)
            models |= proto.gather_models(grpc_method.response_model)
            request_message = proto.get_message_from_model(grpc_method.request_model)
            response_message = proto.get_message_from_model(grpc_method.response_model)

            methods[grpc_method_name] = proto.Method(
                name=grpc_method_name,
                request=request_message,
                response=response_message,
            )
            for model in models:
                message = proto.get_message_from_model(model)
                messages[message.name] = message

        return proto.Service(name=name, methods=methods, messages=messages)

    @staticmethod
    def generate_pb2(
            proto_service: proto.Service,
            proto_path: pathlib.Path,
            grpc_path: pathlib.Path,
            save_proto: bool = False,
    ) -> tuple:
        service_name = proto_service.name.lower()
        try:
            content = proto.render_proto(service=proto_service)
            proto.write_proto(service_name=service_name, proto_path=proto_path,
                              content=content)
            proto.compile_proto(service_name=service_name, proto_path=proto_path,
                                grpc_path=grpc_path)
        finally:
            if not save_proto:
                proto.delete_proto(service_name=service_name, proto_path=proto_path)

        grpc_path = str(grpc_path)
        if grpc_path not in sys.path:
            sys.path.append(grpc_path)
        pb2 = __import__(f"{service_name}_pb2")
        pb2_grpc = __import__(f"{service_name}_pb2_grpc")

        return pb2, pb2_grpc

    @staticmethod
    def generate_client(name: str, grpc_methods: dict[str, Any], pb2, pb2_grpc) -> type:
        class_name = f"{name}Client"
        attributes = {}
        for grpc_method_name, grpc_method in grpc_methods.items():
            async def wrapper(
                    self,
                    request,
                    _grpc_method: GRPCMethod = grpc_method,
            ) -> BaseModel:
                call_rpc = getattr(self.stub, _grpc_method.name)
                grpc_request_message_class = getattr(pb2, _grpc_method.request_model.__name__)
                grpc_request_message = ParseDict(
                    request.model_dump(mode="json"),
                    grpc_request_message_class(),
                )
                grpc_response_message = await call_rpc(request=grpc_request_message)
                grpc_response_dict = MessageToDict(
                    grpc_response_message,
                    preserving_proto_field_name=True,
                )
                return _grpc_method.response_model.model_validate(grpc_response_dict)

            attributes[grpc_method_name] = wrapper
            for alias in grpc_method.aliases:
                attributes[alias] = wrapper

        def __init__(self, host: str, port: int):
            channel = grpc.aio.insecure_channel(f"{host}:{port}")
            self.stub = getattr(pb2_grpc, f"{name}Stub")(channel)

        attributes["__init__"] = __init__

        return type(class_name, (), attributes)


class FastGRPCService(metaclass=FastGRPCServiceMeta):
    is_proxy = True

    def __getattribute__(self, __name: str) -> Any:
        grpc_methods = object.__getattribute__(self, "_grpc_methods")
        if __name in grpc_methods:
            return grpc_methods[__name].__get__(self, self.__class__)
        return object.__getattribute__(self, __name)

    def get_service_name(self) -> str:
        return self.pb2.DESCRIPTOR.services_by_name[self.name].full_name

    @classmethod
    def get_proto(cls) -> str:
        content = proto.render_proto(service=cls._proto_service)
        return content
