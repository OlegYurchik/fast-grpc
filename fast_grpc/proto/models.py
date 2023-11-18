from pydantic import BaseModel

from .enums import TypeEnum


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
