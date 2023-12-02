import inspect
from types import NoneType, UnionType
from typing import (
    Annotated,
    Dict,
    FrozenSet,
    Iterable,
    Sequence,
    Set,
    Tuple,
    Type,
    Union,
    get_origin,
)

from pydantic import BaseModel
from pydantic.fields import FieldInfo

from .enums import TYPE_MAPPING
from .models import Message, Field


def parse_type_sequence(name: str, python_type, args: list) -> Field:
    if len(args) != 1:
        raise TypeError(
            f"Field '{name}': type '{python_type}' must have only one subtype, not {len(args)}.",
        )

    inside_python_type = args[0]
    if inside_python_type in TYPE_MAPPING:
        grpc_type = TYPE_MAPPING[inside_python_type].value
    elif (
            (origin := get_origin(inside_python_type)) is not None and
            origin in (Annotated, Union, UnionType)
    ):
        inside_args = list(inside_python_type.__args__)
        field = parse_type_union(name=name, python_type=inside_python_type, args=inside_args)
        grpc_type = field.type
    elif inspect.isclass(inside_python_type) and issubclass(inside_python_type, BaseModel):
        grpc_type = inside_python_type.__name__
    else:
        raise TypeError(
            f"Field '{name}': unsupported type '{inside_python_type}' in type '{python_type}'.",
        )

    return Field(name=name, type=grpc_type, repeated=True)


def parse_type_mapping(name: str, python_type, args: list) -> Field:
    if len(args) != 2:
        raise TypeError(
            f"Field '{name}': type '{python_type}' must have two subtypes, not {len(args)}.",
        )

    grpc_type = TYPE_MAPPING[dict].value
    python_map_key, python_map_value = args
    map_key, map_value = None, None
    if python_map_key in TYPE_MAPPING:
        map_key = TYPE_MAPPING[python_map_key].value
    elif (
            (origin := get_origin(python_map_key)) is not None and
            origin in (Annotated, Union, UnionType)
    ):
        python_map_key_args = list(python_map_key.__args__)
        field = parse_type_union(name=name, python_type=python_map_key,
                                 args=python_map_key_args)
        map_key = field.type
    else:
        raise TypeError(
            f"Field '{name}': unsupported type '{python_map_key}' in type '{python_type}'.",
        )

    if python_map_value in TYPE_MAPPING:
        map_value = TYPE_MAPPING[python_map_value].value
    elif (
            (origin := get_origin(python_map_value)) is not None and
            origin in (Annotated, Union, UnionType)
    ):
        python_map_value_args = list(python_map_value.__args__)
        field = parse_type_union(name=name, python_type=python_map_value,
                                 args=python_map_value_args)
        map_value = field.type
    elif inspect.isclass(python_map_value) and issubclass(python_map_value, BaseModel):
        map_value = python_map_value.__name__
    else:
        raise TypeError(
            f"Field '{name}': unsupported type '{python_map_value}' in type '{python_type}'.",
        )

    return Field(
        name=name,
        type=grpc_type,
        map_key=map_key,
        map_value=map_value,
    )


def parse_type_union(name: str, python_type, args: list) -> Field:
    if NoneType in args:
        args.remove(NoneType)
    if len(args) != 1:
        raise TypeError(
            f"Field '{name}': type '{python_type}' must have only one subtype, not {len(args)}. "
            "Tip: None/Optional type ignoring."
        )

    inside_python_type = args[0]
    if inside_python_type in TYPE_MAPPING:
        grpc_type = TYPE_MAPPING[inside_python_type].value
    elif (
            (origin := get_origin(inside_python_type)) is not None and
            origin in (Annotated, Union, UnionType)
    ):
        inside_args = list(inside_python_type.__args__)
        field = parse_type_union(name, inside_python_type, inside_args)
        grpc_type = field.type
    elif inspect.isclass(inside_python_type) and issubclass(inside_python_type, BaseModel):
        grpc_type = inside_python_type.__name__
    else:
        raise TypeError(
            f"Field '{name}': unsupported type '{inside_python_type}' in type {python_type}'.",
        )

    return Field(name=name, type=grpc_type)


def parse_field(name: str, field: FieldInfo) -> Field:
    repeated = False
    map_key, map_value = None, None
    python_type = field.annotation
    if python_type in TYPE_MAPPING:
        grpc_type = TYPE_MAPPING[python_type].value
    elif (origin := get_origin(python_type)) is not None:
        args = list(python_type.__args__)
        if origin in (Union, UnionType):
            return parse_type_union(name, python_type, args)
        if issubclass(origin, (dict, Dict)):
            return parse_type_mapping(name, python_type, args)
        if issubclass(origin, (list, tuple, set, frozenset, Iterable, Sequence, Tuple, Set,
                               FrozenSet)):
            return parse_type_sequence(name, python_type, args)
        raise TypeError(f"Field '{name}': unsupported type '{python_type}'.")
    elif inspect.isclass(python_type) and issubclass(python_type, BaseModel):
        grpc_type = python_type.__name__
    else:
        raise TypeError(f"Field '{name}': unsupported type '{python_type}'.")

    return Field(
        name=name,
        repeated=repeated,
        type=grpc_type,
        map_key=map_key,
        map_value=map_value,
    )


def get_message_from_model(model: Type[BaseModel]) -> Message:
    fields = {}

    for name, field in model.model_fields.items():
        fields[name] = parse_field(name=name, field=field)

    return Message(name=model.__name__, fields=fields)


def gather_models(model: Type[BaseModel]) -> set[Type[BaseModel]]:
    models = set()
    stack = [model]
    processed = set()

    while stack:
        model = stack.pop()
        models.add(model)
        processed.add(model)
        
        for field in model.model_fields.values():
            arg_stack = [field.annotation]
            while arg_stack:
                arg = arg_stack.pop()
                if get_origin(arg) is not None:
                    arg_stack.extend(arg.__args__)
                elif (
                        inspect.isclass(arg) and
                        issubclass(arg, BaseModel) and
                        arg not in processed and
                        arg not in stack
                ):
                    stack.append(arg)

    return models
