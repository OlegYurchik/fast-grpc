import pathlib

import pytest

from fast_grpc.proto.utils import compile_proto, delete_proto, render_proto, write_proto


@pytest.mark.skip("Need implement test")
def test_render_proto():
    render_proto(service=service)


@pytest.mark.skip("Need implement test")
def test_write_proto(tmp_path: pathlib.Path):
    write_proto(service=service, proto_path=tmp_path, content=content)


@pytest.mark.skip("Need implement test")
def test_compile_proto(tmp_path: pathlib.Path):
    compile_proto(service=service, proto_path=tmp_path, grpc_path=tmp_path)


@pytest.mark.skip("Need implement test")
def test_delete_proto(tmp_path: pathlib.Path):
    delete_proto(service=service, proto_path=tmp_path)
