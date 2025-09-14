import enum
import pathlib
import uuid
from functools import reduce
from typing import Dict, FrozenSet, Iterable, List, Sequence, Set, Tuple, Type, Union

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

from fast_grpc.proto.models import Field, MapField, Message
from fast_grpc.proto.parse import (
    gather_enums_from_model,
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
    FirstModelEnum,
    FourthModel,
    RootModel,
    RootModelEnum,
    SecondModel,
    ThirdModel,
)


BASE_TYPES = (
    (int, "int64"),
    (float, "double"),
    (bool, "bool"),
    (bytes, "bytes"),
    (str, "string"),
    (RootModelEnum, "RootModelEnum"),
    (uuid.UUID, "string"),
    (pathlib.Path, "string"),
)
ANNOTATED_TYPES = (
    (conint(ge=-10, le=10), "int64"),
    (NonPositiveInt, "int64"),
    (NegativeInt, "int64"),
    (NonNegativeInt, "int64"),
    (PositiveInt, "int64"),
    (confloat(ge=0, le=1), "double"),
    (constr(strip_whitespace=True, min_length=1), "string"),
    (EmailStr, "string"),
)
TYPES = (
    *BASE_TYPES,
    *ANNOTATED_TYPES,
    (type("PydanticMessage", (BaseModel,), {}), "PydanticMessage"),
)
BASE_OPTIONAL_TYPES = tuple(
    (reduce(lambda item, _: item | None, range(1, index + 1), python_type), grpc_type)
    for python_type, grpc_type in BASE_TYPES
    for index in range(1, 2)
)
OPTIONAL_TYPES = tuple(
    (reduce(lambda item, _: item | None, range(1, index + 1), python_type), grpc_type)
    for python_type, grpc_type in TYPES
    for index in range(1, 2)
)
SEQUENCE_TYPES = (list, tuple, set, frozenset, List, Tuple, Set, FrozenSet, Sequence, Iterable)


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


@pytest.mark.parametrize(("name", "python_type", "field"), (
    *(
        ("test", python_type, Field(name="test", type=grpc_type))
        for python_type, grpc_type in TYPES
    ),
    *(
        ("test", python_type, Field(name="test", type=grpc_type, optional=True))
        for python_type, grpc_type in OPTIONAL_TYPES
    ),
    *(
        (
            "test",
            outside_python_type[inside_python_type],
            Field(name="test", type=grpc_type, repeated=True),
        )
        for inside_python_type, grpc_type in (*TYPES, *OPTIONAL_TYPES)
        for outside_python_type in SEQUENCE_TYPES
    ),
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
def test_parse_type(name: str, python_type: type, field: Field):
    result = parse_type(name=name, python_type=python_type)

    assert result == field


@pytest.mark.parametrize("python_type", (
    type("A", (), {}),
))
def test_parse_type_unsupported_type(faker: Faker, python_type: type):
    name = faker.first_name()
    exception_message = (
        f"Field '{name}': unsupported type '{python_type}'."
    )

    with pytest.raises(TypeError) as exception:
        parse_type(name=name, python_type=python_type)

    assert exception.value.args[0] == exception_message


@pytest.mark.parametrize(
    ("python_type", "grpc_type"),
    (*TYPES, *OPTIONAL_TYPES),
)
def test_parse_type_union(faker: Faker, python_type: type, grpc_type: str):
    name = faker.first_name()

    result = parse_type_union(
        name=name,
        python_type=Union[python_type, None],
    )

    assert result.name == name
    assert result.type == grpc_type
    assert result.repeated is False


@pytest.mark.parametrize(
    "python_type",
    (
        *(python_type for python_type, _ in BASE_TYPES),
        # Because union with one subtype is not union
        *(Union[python_type] for python_type, _ in BASE_TYPES),
    ),
)
def test_parse_type_union_not_union(faker: Faker, python_type: type):
    name = faker.last_name()
    exception_message = (
        f"Field '{name}': type '{python_type}' is not union."
    )

    with pytest.raises(TypeError) as exception:
        parse_type_union(name=name, python_type=python_type)

    assert exception.value.args[0] == exception_message


@pytest.mark.parametrize(("python_type", "subtypes_count"), (
    (Union[int, float], 2),
    (Union[str, bytes, list], 3),
    (Union[pathlib.Path, complex, bytearray, None], 3),
))
def test_parse_type_union_incorrect_subtypes_count(
        faker: Faker,
        python_type: type,
        subtypes_count: int,
):
    name = faker.last_name()
    exception_message = (
        f"Field '{name}': type '{python_type}' must have only one subtype, not {subtypes_count}. "
        "Tip: None/Optional type ignoring."
    )

    with pytest.raises(TypeError) as exception:
        parse_type_union(name=name, python_type=python_type)

    assert exception.value.args[0] == exception_message


@pytest.mark.parametrize("python_type", (dict, Dict))
@pytest.mark.parametrize(
    ("key_type", "grpc_key_type"),
    BASE_TYPES,
)
@pytest.mark.parametrize(
    ("value_type", "grpc_value_type"),
    (*TYPES, *OPTIONAL_TYPES),
)
def test_parse_type_mapping(faker: Faker, python_type: type, key_type: type, grpc_key_type: str,
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
    "python_type",
    tuple(python_type for python_type, _ in BASE_TYPES),
)
def test_parse_type_mapping_not_mapping(faker: Faker, python_type: type):
    name = faker.last_name()
    exception_message = f"Field '{name}': type '{python_type}' is not mapping."

    with pytest.raises(TypeError) as exception:
        parse_type_mapping(name=name, python_type=python_type)

    assert exception.value.args[0] == exception_message


@pytest.mark.parametrize(("python_type", "subtypes_count"), (
    (dict[int], 1),
    (dict[str, bytes, list], 3),
    (dict[pathlib.Path, complex, bytearray, None], 4),
))
def test_parse_type_mapping_incorrect_subtypes_count(
        faker: Faker,
        python_type: type,
        subtypes_count: int,
):
    name = faker.last_name()
    exception_message = (
        f"Field '{name}': type '{python_type}' must have two subtypes, not {subtypes_count}."
    )

    with pytest.raises(TypeError) as exception:
        parse_type_mapping(name=name, python_type=python_type)

    assert exception.value.args[0] == exception_message


@pytest.mark.parametrize("python_type", SEQUENCE_TYPES)
@pytest.mark.parametrize(
    ("inside_python_type", "grpc_type"),
    (*TYPES, *OPTIONAL_TYPES),
)
def test_parse_type_sequence(
        faker: Faker,
        python_type: type,
        inside_python_type: type,
        grpc_type: str,
):
    name = faker.first_name()
    result = parse_type_sequence(
        name=name,
        python_type=python_type[inside_python_type],
    )

    assert result.name == name
    assert result.type == grpc_type
    assert result.repeated is True


@pytest.mark.parametrize("python_type", (list, tuple, set, frozenset))
@pytest.mark.parametrize(("subtypes", "subtypes_count"), (
    ([int, float], 2),
    ([str, bytes, list], 3),
    ([pathlib.Path, complex, bytearray, None], 4),
))
def test_parse_type_sequence_incorrect_subtypes_count(
        faker: Faker,
        python_type: type,
        subtypes: Iterable[type],
        subtypes_count: int,
):
    name = faker.last_name()
    python_type = python_type[*subtypes]
    exception_message = (
        f"Field '{name}': type '{python_type}' must have only one subtype, not {subtypes_count}."
    )

    with pytest.raises(TypeError) as exception:
        parse_type_sequence(name=name, python_type=python_type)

    assert exception.value.args[0] == exception_message


@pytest.mark.parametrize(("model", "expected_models"), (
    (RootModel, {"RootModel": RootModel}),
    (FirstModel, {"RootModel": RootModel, "FirstModel": FirstModel}),
    (SecondModel, {
        "RootModel": RootModel,
        "FirstModel": FirstModel,
        "SecondModel": SecondModel,
    }),
    (ThirdModel, {"ThirdModel": ThirdModel}),
    (FourthModel, {
        "RootModel": RootModel,
        "FirstModel": FirstModel,
        "SecondModel": SecondModel,
        "FourthModel": FourthModel,
    }),
))
def test_gather_models(model: Type[BaseModel], expected_models: dict[type[BaseModel]]):
    models = gather_models(model=model)

    assert models == expected_models


@pytest.mark.parametrize(("model", "expected_enums"), (
    (RootModel, {"RootModelEnum": RootModelEnum}),
    (FirstModel, {"RootModelEnum": RootModelEnum, "FirstModelEnum": FirstModelEnum}),
))
def test_gather_enums_from_model(
    model: type[BaseModel],
    expected_enums: dict[str, type[enum.Enum]],
):
    enums = gather_enums_from_model(model=model)

    assert enums == expected_enums
