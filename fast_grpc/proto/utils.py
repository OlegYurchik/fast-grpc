import pathlib
from typing import Type

import jinja2
from grpc_tools import protoc
from pydantic import BaseModel

from .enums import TYPE_MAPPING
from .models import Field, Message, Service


TEMPLATE_DIR_PATH = pathlib.Path(__file__).parent / "templates"
JINJA_ENV = jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATE_DIR_PATH))


def get_fields_from_model(model: Type[BaseModel]) -> dict[str, Field]:
    fields = {}

    for name, field in model.__fields__.items():
        if field.annotation in TYPE_MAPPING:
            grpc_type = TYPE_MAPPING[field.annotation]
        else:
            raise TypeError()

        fields[name] = Field(name=name, type=grpc_type)

    return fields


def get_message_from_model(model: Type[BaseModel]) -> Message:
    return Message(name=model.__name__, fields=get_fields_from_model(model))


def render_proto(service: Service, proto_path: pathlib.Path):
    template = JINJA_ENV.get_template("service.proto")
    content = template.render(service=service)
    proto_file_path = proto_path / f"{service.name.lower()}.proto"
    proto_file_path.write_text(content)


def compile_proto(service: Service, proto_path: pathlib.Path, grpc_path: pathlib.Path):
    protoc_args = [
        f"--proto_path={proto_path}",
        f"--python_out={grpc_path}",
        f"--grpc_python_out={grpc_path}",
        str(proto_path / f"{service.name.lower()}.proto"),
        f"--proto_path={proto_path}",
    ]
    status_code = protoc.main(protoc_args)

    if status_code != 0:
        raise Exception("Protobuf compilation failed")


def delete_proto(service: Service, proto_path: pathlib.Path):
    proto_file_path = proto_path / f"{service.name.lower()}.proto"
    proto_file_path.unlink(missing_ok=True)
