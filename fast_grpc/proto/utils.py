import pathlib

import jinja2
from grpc_tools import protoc

from .models import Service


TEMPLATE_DIR_PATH = pathlib.Path(__file__).parent / "templates"
JINJA_ENV = jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATE_DIR_PATH), trim_blocks=True)


def render_proto(service: Service):
    template = JINJA_ENV.get_template("service.proto")
    return template.render(service=service)


def compile_proto(proto_file: pathlib.Path, proto_path: pathlib.Path, grpc_path: pathlib.Path):
    grpc_path.mkdir(parents=True, exist_ok=True)
    protoc_args = [
        f"--proto_path={proto_path}",
        f"--python_out={grpc_path}",
        f"--grpc_python_out={grpc_path}",
        str(proto_file),
        f"--proto_path={proto_path}",
    ]
    status_code = protoc.main(protoc_args)

    if status_code != 0:
        raise RuntimeError("Protobuf compilation failed")
