import pathlib

from faker import Faker

from fast_grpc.proto import Service, compile_proto, delete_proto, render_proto, write_proto


def test_render_proto(faker: Faker):
    name = faker.first_name()
    service = Service(name=name, methods={}, messages={})

    proto_content = render_proto(service=service).strip()
    expected_proto_content = (
        "syntax = \"proto3\";\n"
        f"package {name.lower()};\n"
        "\n"
        f'service {name} {{\n'
        "}"
    )

    assert proto_content == expected_proto_content


def test_write_proto(tmp_path: pathlib.Path):
    content = """
    syntax = "proto3";
    package test;
    
    service Test {}
    """

    write_proto(service_name="Test", proto_path=tmp_path, content=content)

    assert (tmp_path / "test.proto").read_text().strip() == content.strip()


def test_compile_proto(tmp_path: pathlib.Path):
    proto_content = """
    syntax = "proto3";
    package test;

    service Test {}
    """
    (tmp_path / "test.proto").write_text(data=proto_content)

    compile_proto(service_name="Test", proto_path=tmp_path, grpc_path=tmp_path)

    assert (tmp_path / "test_pb2.py").is_file() and (tmp_path / "test_pb2_grpc.py").is_file()


def test_delete_proto(tmp_path: pathlib.Path):
    proto_content = """
    syntax = "proto3";
    package test;

    service Test {}
    """
    (tmp_path / "test.proto").write_text(data=proto_content)

    delete_proto(service_name="Test", proto_path=tmp_path)

    assert not (tmp_path / "test.proto").is_file()
