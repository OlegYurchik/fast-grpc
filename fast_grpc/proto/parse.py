import enum
import inspect
from types import NoneType, UnionType
from typing import Annotated, Iterable, Union, get_origin

from pydantic import BaseModel

from .models import Field, MapField, Message
from .type_mappings import ORIGIN_TYPES_MAPPING, TYPE_MAPPING


def get_message_from_model(model: type[BaseModel]) -> Message:
    fields = {}

    for name, field in model.model_fields.items():
        fields[name] = parse_type(name=name, python_type=field.annotation)

    return Message(name=model.__name__, fields=fields)


def parse_type(name: str, python_type: type, allow_pydantic_model: bool = True) -> Field:
    if python_type in TYPE_MAPPING:
        return Field(name=name, type=TYPE_MAPPING[python_type])

    if (origin := get_origin(python_type)):
        if origin in (Annotated, Union, UnionType):
            return parse_type_union(name=name, python_type=python_type)
        if issubclass(origin, dict):
            return parse_type_mapping(name=name, python_type=python_type)
        if issubclass(origin, Iterable):
            return parse_type_sequence(name=name, python_type=python_type)

    if inspect.isclass(python_type):
        if issubclass(python_type, enum.Enum):
            return Field(name=name, type=python_type.__name__)
        if (
                allow_pydantic_model and
                issubclass(python_type, BaseModel)
        ):
            return Field(name=name, type=python_type.__name__)
        for type_ in ORIGIN_TYPES_MAPPING:
            if issubclass(python_type, type_):
                return Field(name=name, type=ORIGIN_TYPES_MAPPING[type_])

    raise TypeError(f"Field '{name}': unsupported type '{python_type}'.")


def parse_type_union(name: str, python_type: type) -> Field:
    if not hasattr(python_type, "__args__"):
        raise TypeError(f"Field '{name}': type '{python_type}' is not union.")

    optional = False
    args = list(python_type.__args__)
    if NoneType in args:
        args.remove(NoneType)
        optional = True
    if len(args) != 1:
        raise TypeError(
            f"Field '{name}': type '{python_type}' must have only one subtype, not {len(args)}. "
            "Tip: None/Optional type ignoring."
        )

    field = parse_type(name=name, python_type=args[0])
    field.optional = optional
    return field


def parse_type_mapping(name: str, python_type: type) -> Field:
    if not hasattr(python_type, "__args__"):
        raise TypeError(f"Field '{name}': type '{python_type}' is not mapping.")

    args = tuple(python_type.__args__)
    if len(args) != 2:
        raise TypeError(
            f"Field '{name}': type '{python_type}' must have two subtypes, not {len(args)}.",
        )

    python_key_type, python_value_type = args
    key_field = parse_type(name=name, python_type=python_key_type, allow_pydantic_model=False)
    value_field = parse_type(name=name, python_type=python_value_type)

    return MapField(
        name=name,
        key=key_field.type,
        value=value_field.type,
    )


def parse_type_sequence(name: str, python_type: type) -> Field:
    args = tuple(python_type.__args__)
    if len(args) != 1:
        raise TypeError(
            f"Field '{name}': type '{python_type}' must have only one subtype, not {len(args)}.",
        )

    field = parse_type(name=name, python_type=args[0])
    field.optional = False
    field.repeated = True

    return field


def gather_models(model: type[BaseModel]) -> dict[str, type[BaseModel]]:
    models = {}
    stack = [model]
    processed = set()

    while stack:
        model = stack.pop()
        models[model.__name__] = model
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


def gather_enums_from_model(model: type[BaseModel]) -> dict[str, type[enum.Enum]]:
    enums = {}
    processed = set()
    arg_stack = [field.annotation for field in model.model_fields.values()]

    while arg_stack:
        arg = arg_stack.pop()
        if get_origin(arg) is not None:
            arg_stack.extend(arg.__args__)
        elif (
                inspect.isclass(arg) and
                issubclass(arg, BaseModel) and
                arg not in processed
        ):
            arg_stack.extend(field.annotation for field in arg.model_fields.values())
        elif (
                inspect.isclass(arg) and
                issubclass(arg, enum.Enum) and
                arg not in processed
        ):
            enums[arg.__name__] = arg
        processed.add(arg)

    return enums
