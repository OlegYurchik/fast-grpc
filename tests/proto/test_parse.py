import enum
import pathlib
import uuid
from functools import reduce
from typing import Dict, FrozenSet, Iterable, List, Optional, Sequence, Set, Tuple, Type, Union

import pytest
from faker import Faker
from pydantic import (
    BaseModel,
    EmailStr,
    NegativeInt,
    NonNegativeInt,
    NonPositiveInt,
    PositiveInt,
    confloat,
    conint,
    constr,
)
from pydantic.fields import FieldInfo

from fast_grpc.proto.models import Field, MapField, Message
from fast_grpc.proto.parse import (
    gather_models,
    get_message_from_model,
    parse_type,
    parse_type_mapping,
    parse_type_sequence,
    parse_type_union,
)

from .models import (
    FIRST_FIELDS,
    FOURTH_FIELDS,
    ROOT_FIELDS,
    SECOND_FIELDS,
    THIRD_FIELDS,
    FirstModel,
    FourthModel,
    RootModel,
    RootModelEnum,
    SecondModel,
    ThirdModel,
)


BASE_TYPES = (
    (int, "int64"),
    (conint(ge=-10, le=10), "int64"),
    (NonPositiveInt, "int64"),
    (NegativeInt, "int64"),
    (NonNegativeInt, "int64"),
    (PositiveInt, "int64"),
    (float, "double"),
    (confloat(ge=0, le=1), "double"),
    (bool, "bool"),
    (bytes, "bytes"),
    (str, "string"),
    (constr(strip_whitespace=True, min_length=1), "string"),
    (EmailStr, "string"),
    (uuid.UUID, "string"),
    (pathlib.Path, "string"),
    (RootModelEnum, "RootModelEnum"),
)
TYPES = (
    *BASE_TYPES,
    (type("PydanticMessage", (BaseModel,), {}), "PydanticMessage"),
)
BASE_TYPES_OPTIONAL = (
    (reduce(lambda item, _: item | None, range(index), python_type), grpc_type)
    for python_type, grpc_type in BASE_TYPES
    for index in range(2)
)
TYPES_OPTIONAL = (
    (reduce(lambda item, _: item | None, range(index), python_type), grpc_type)
    for python_type, grpc_type in TYPES
    for index in range(2)
)
SEQUENCE_TYPES = (list, tuple, set, frozenset, List, Tuple, Set, FrozenSet, Sequence, Iterable)


@pytest.mark.parametrize(("name", "annotation", "field"), (
    *[
        ("test", python_type, Field(name="test", type=grpc_type))
        for python_type, grpc_type in (*TYPES, *TYPES_OPTIONAL)
    ],
    *[
        (
            "test",
            outside_python_type[inside_python_type],
            Field(name="test", type=grpc_type, repeated=True),
        )
        for inside_python_type, grpc_type in (*TYPES, *TYPES_OPTIONAL)
        for outside_python_type in SEQUENCE_TYPES
    ],
    *[
        (
            "test",
            outside_python_type[python_key_type, python_value_type],
            MapField(name="test", key=key_type, value=value_type),
        )
        for python_key_type, key_type in BASE_TYPES
        for python_value_type, value_type in TYPES
        for outside_python_type in (dict, Dict)
    ],
))
def test_parse_type(name: str, annotation, field: Field):
    result = parse_type(name=name, python_type=annotation)

    assert result == field


@pytest.mark.parametrize("python_type", SEQUENCE_TYPES)
@pytest.mark.parametrize(
    ("inside_python_type", "grpc_type"),
    (*TYPES, *TYPES_OPTIONAL),
)
def test_parse_type_sequence(faker: Faker, python_type, inside_python_type, grpc_type: str):
    name = faker.first_name()
    result = parse_type_sequence(
        name=name,
        python_type=python_type[inside_python_type],
    )

    assert result.name == name
    assert result.type == grpc_type
    assert result.repeated is True


@pytest.mark.parametrize("python_type", (dict, Dict))
@pytest.mark.parametrize(
    ("key_type", "grpc_key_type"),
    BASE_TYPES,
)
@pytest.mark.parametrize(
    ("value_type", "grpc_value_type"),
    (*TYPES, *TYPES_OPTIONAL),
)
def test_parse_type_mapping(faker: Faker, python_type, key_type: type, grpc_key_type: str,
                            value_type: type, grpc_value_type: str):
    name = faker.first_name()
    result = parse_type_mapping(
        name=name,
        python_type=python_type[key_type, value_type],
    )

    assert result.name == name
    assert result.type == "map"
    assert result.repeated is False
    assert result.key == grpc_key_type
    assert result.value == grpc_value_type


@pytest.mark.parametrize(
    ("python_type", "grpc_type"),
    (*TYPES, *TYPES_OPTIONAL),
)
def test_parse_type_union(faker: Faker, python_type, grpc_type: str):
    name = faker.first_name()
    result = parse_type_union(
        name=name,
        python_type=Union[python_type, None],
    )

    assert result.name == name
    assert result.type == grpc_type
    assert result.repeated is False



@pytest.mark.parametrize(("model", "expected_message"), (
    (RootModel, Message(name="RootModel", fields=ROOT_FIELDS)),
    (FirstModel, Message(name="FirstModel", fields=FIRST_FIELDS)),
    (SecondModel, Message(name="SecondModel", fields=SECOND_FIELDS)),
    (ThirdModel, Message(name="ThirdModel", fields=THIRD_FIELDS)),
    (FourthModel, Message(name="FourthModel", fields=FOURTH_FIELDS)),
))
def test_get_message_from_model(model: Type[BaseModel], expected_message: Message):
    message = get_message_from_model(model=model)

    assert message.name == expected_message.name
    assert len(message.fields) == len(expected_message.fields)
    for name, field in message.fields.items():
        assert name in expected_message.fields

        expected_field = expected_message.fields[name]
        assert field == expected_field


@pytest.mark.parametrize(("model", "expected_models"), (
    (RootModel, {RootModel}),
    (FirstModel, {RootModel, FirstModel}),
    (SecondModel, {RootModel, FirstModel, SecondModel}),
    (ThirdModel, {ThirdModel}),
    (FourthModel, {RootModel, FirstModel, SecondModel, FourthModel}),
))
def test_gather_models(model: Type[BaseModel], expected_models: set[Type[BaseModel]]):
    models = gather_models(model=model)

    assert models == expected_models
