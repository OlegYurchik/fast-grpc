from types import NoneType
from typing import Type, Union, get_origin

from pydantic import BaseModel

from .enums import TYPE_MAPPING, TypeEnum


class Field(BaseModel):
    name: str
    type: TypeEnum
    repeated: bool = False


class Message(BaseModel):
    name: str
    fields: dict[str, Field]


class Method(BaseModel):
    name: str
    request: Message
    response: Message


class Service(BaseModel):
    name: str
    methods: dict[str, Method]
    messages: dict[str, Message]


def get_fields_from_model(model: Type[BaseModel]) -> dict[str, Field]:
    fields = {}

    for name, field in model.__fields__.items():
        if field.annotation in TYPE_MAPPING:
            grpc_type = TYPE_MAPPING[field.annotation]
        elif get_origin(field.annotation) is Union:
            args = list(field.annotation.__args__)
            if NoneType in field.annotation.__args__:
                args.remove(NoneType)
            if len(args) != 1 or args[0] not in TYPE_MAPPING:
                raise TypeError()
            grpc_type = TYPE_MAPPING[args[0]]
        else:
            raise TypeError()

        fields[name] = Field(name=name, type=grpc_type)

    return fields


def get_message_from_model(model: Type[BaseModel]) -> Message:
    return Message(name=model.__name__, fields=get_fields_from_model(model))
