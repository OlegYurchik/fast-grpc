import pathlib
import uuid
from functools import reduce
from typing import Dict, FrozenSet, Iterable, List, Optional, Set, Sequence, Tuple, Type, Union

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

from fast_grpc.proto.enums import TypeEnum
from fast_grpc.proto.models import Field, Message
from fast_grpc.proto.parse import (
    gather_models,
    get_message_from_model,
    parse_field,
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
    SecondModel,
    ThirdModel,
)


BASE_TYPES = [
    (int, TypeEnum.INT64),
    (conint(ge=-10, le=10), TypeEnum.INT64),
    (NonPositiveInt, TypeEnum.INT64),
    (NegativeInt, TypeEnum.INT64),
    (NonNegativeInt, TypeEnum.INT64),
    (PositiveInt, TypeEnum.INT64),
    (float, TypeEnum.DOUBLE),
    (confloat(ge=0, le=1), TypeEnum.DOUBLE),
    (bool, TypeEnum.BOOL),
    (bytes, TypeEnum.BYTES),
    (str, TypeEnum.STRING),
    (constr(strip_whitespace=True, min_length=1), TypeEnum.STRING),
    (EmailStr, TypeEnum.STRING),
    (uuid.UUID, TypeEnum.STRING),
    (pathlib.Path, TypeEnum.STRING),
]
TYPES = [
    *BASE_TYPES,
    (type("PydanticMessage", (BaseModel,), {}), "PydanticMessage"),
]
BASE_TYPES_OPTIONAL = [
    (reduce(lambda item, _: item | None, range(index), python_type), grpc_type)
    for python_type, grpc_type in BASE_TYPES
    for index in range(2)
]
TYPES_OPTIONAL = [
    (reduce(lambda item, _: item | None, range(index), python_type), grpc_type)
    for python_type, grpc_type in TYPES
    for index in range(2)
]
SEQUENCE_TYPES = [list, tuple, set, frozenset, List, Tuple, Set, FrozenSet, Sequence, Iterable]


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
        args=[inside_python_type],
    )

    assert result.name == name
    assert result.type == grpc_type
    assert result.repeated is True
    assert result.map_key is None
    assert result.map_value is None


@pytest.mark.parametrize("python_type", SEQUENCE_TYPES)
@pytest.mark.parametrize("args", (
    [],
    [int, str],
    [str, float, int],
    [type("A", (BaseModel,), {}), bool],
))
def test_parse_type_sequence_incorrect_args(faker: Faker, python_type, args: list):
    name = faker.first_name()
    exception_text = (
        f"Field '{name}': type '{python_type}' must have only one subtype, not {len(args)}."
    )

    with pytest.raises(TypeError) as exception:
        parse_type_sequence(name=name, python_type=python_type, args=args)

    assert exception.value.args[0] == exception_text


@pytest.mark.parametrize("python_type", SEQUENCE_TYPES)
@pytest.mark.parametrize("inside_python_type", (
    "literal",
    type("A", (), {"name": "Oleg"}),
))
def test_parse_type_sequence_unsupported_type(faker: Faker, python_type, inside_python_type):
    name = faker.first_name()
    exception_text = (
        f"Field '{name}': unsupported type '{inside_python_type}' in type '{python_type}'."
    )

    with pytest.raises(TypeError) as exception:
        parse_type_sequence(name=name, python_type=python_type, args=[inside_python_type])

    assert exception.value.args[0] == exception_text


@pytest.mark.parametrize("python_type", (dict, Dict))
@pytest.mark.parametrize(
    ("key", "map_key"),
    BASE_TYPES,
)
@pytest.mark.parametrize(
    ("value", "map_value"),
    (*TYPES, *TYPES_OPTIONAL),
)
def test_parse_type_mapping(faker: Faker, python_type, key: type, map_key: TypeEnum, value: type,
                            map_value: TypeEnum):
    name = faker.first_name()
    result = parse_type_mapping(name=name, python_type=python_type[key, value], args=[key, value])

    assert result.name == name
    assert result.type == TypeEnum.MAP
    assert result.repeated is False
    assert result.map_key == map_key
    assert result.map_value == map_value


@pytest.mark.parametrize("python_type", SEQUENCE_TYPES)
@pytest.mark.parametrize("args", (
    [],
    [int],
    [str, float, int],
    [bool, type("A", (BaseModel,), {}), bytes, bytearray],
))
def test_parse_type_mapping_incorrect_args(faker: Faker, python_type, args: list):
    name = faker.first_name()
    exception_text = (
        f"Field '{name}': type '{python_type}' must have two subtypes, not {len(args)}."
    )

    with pytest.raises(TypeError) as exception:
        parse_type_mapping(name=name, python_type=python_type, args=args)

    assert exception.value.args[0] == exception_text


@pytest.mark.parametrize("python_type", (dict, Dict))
@pytest.mark.parametrize(("python_key_type", "python_value_type"), (
    ("literal", 2),
    (str, 2),
    (2, int),
    (type("A", (BaseModel,), {}), int),
    (int, type("A", (), {"name": "Oleg"})),
))
def test_parse_type_mapping_unsupported_type(
        faker: Faker,
        python_type,
        python_key_type,
        python_value_type,
):
    name = faker.first_name()
    exception_texts = (
        f"Field '{name}': unsupported type '{python_key_type}' in type '{python_type}'.",
        f"Field '{name}': unsupported type '{python_value_type}' in type '{python_type}'.",
    )

    with pytest.raises(TypeError) as exception:
        parse_type_mapping(
            name=name,
            python_type=python_type,
            args=[python_key_type, python_value_type],
    )

    assert exception.value.args[0] in exception_texts


@pytest.mark.parametrize("python_type", (Union, Optional))
@pytest.mark.parametrize(
    ("inside_python_type", "grpc_type"),
    (*TYPES, *TYPES_OPTIONAL),
)
def test_parse_type_union(faker: Faker, python_type, inside_python_type, grpc_type: str):
    name = faker.first_name()
    result = parse_type_union(
        name=name,
        python_type=python_type[inside_python_type],
        args=[inside_python_type],
    )

    assert result.name == name
    assert result.type == grpc_type
    assert result.repeated is False
    assert result.map_key is None
    assert result.map_value is None


@pytest.mark.parametrize("python_type", (Union, Optional))
@pytest.mark.parametrize("args", (
    [],
    [int, str],
    [bool, float, int],
))
def test_parse_type_union_incorrect_args(faker: Faker, python_type, args: list):
    name = faker.first_name()
    exception_text = (
        f"Field '{name}': type '{python_type}' must have only one subtype, not {len(args)}. "
        "Tip: None/Optional type ignoring."
    )

    with pytest.raises(TypeError) as exception:
        parse_type_union(name=name, python_type=python_type, args=args)

    assert exception.value.args[0] == exception_text


@pytest.mark.parametrize("python_type", (Union, Optional))
@pytest.mark.parametrize("inside_python_type", (
    "literal",
    type("A", (), {}),
))
def test_parse_type_union_unsupported_type(faker: Faker, python_type, inside_python_type):
    name = faker.first_name()
    exception_text = (
        f"Field '{name}': unsupported type '{inside_python_type}' in type '{python_type}'."
    )

    with pytest.raises(TypeError) as exception:
        parse_type_union(
            name=name,
            python_type=python_type,
            args=[inside_python_type],
        )

    assert exception.value.args[0] == exception_text


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
            Field(name="test", type=TypeEnum.MAP, map_key=key_type, map_value=value_type),
        )
        for python_key_type, key_type in BASE_TYPES
        for python_value_type, value_type in TYPES
        for outside_python_type in (dict, Dict)
    ],
))
def test_parse_field(name: str, annotation, field: Field):
    field_info = FieldInfo(annotation=annotation)
    result = parse_field(name=name, field=field_info)

    assert result.name == field.name
    assert result.type == field.type
    assert result.repeated == field.repeated
    assert result.map_key == field.map_key
    assert result.map_value == field.map_value


@pytest.mark.parametrize("annotation", (
    "literal",
    type("A", (), {}),
))
def test_parse_field_unsupported_type(faker: Faker, annotation):
    name = faker.first_name()
    exception_text = f"Field '{name}': unsupported type '{annotation}'."
    field_info = FieldInfo(annotation=annotation)
    
    with pytest.raises(TypeError) as exception:
        parse_field(name=name, field=field_info)

    assert exception.value.args[0] == exception_text


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
        assert field.name == expected_field.name
        assert field.type == expected_field.type
        assert field.repeated == expected_field.repeated
        assert field.map_key == expected_field.map_key
        assert field.map_value == expected_field.map_value


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
