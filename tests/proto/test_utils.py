import pathlib

from faker import Faker

from fast_grpc.proto import Service, compile_proto, render_proto


def test_render_proto(faker: Faker):
    name = faker.first_name()
    package_name = faker.last_name().lower()
    service = Service(package_name=package_name, name=name, methods={}, messages={}, enums={})

    proto_content = render_proto(service=service).strip()
    expected_proto_content = (
        "syntax = \"proto3\";\n"
        f"package {package_name};\n"
        "\n"
        f'service {name} {{\n'
        "}"
    )

    assert proto_content == expected_proto_content


def test_compile_proto(tmp_path: pathlib.Path):
    proto_content = """
    syntax = "proto3";
    package test;

    service Test {}
    """
    proto_file = tmp_path / "test.proto"
    proto_file.write_text(data=proto_content)
    expected_pb2_file = tmp_path / "test_pb2.py"
    expected_pb2_grpc_file = tmp_path / "test_pb2_grpc.py"

    compile_proto(proto_file=proto_file, proto_path=tmp_path, grpc_path=tmp_path)

    assert expected_pb2_file.is_file() and expected_pb2_grpc_file.is_file()
