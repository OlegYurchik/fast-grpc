import enum
from typing import Literal

from pydantic import BaseModel


class Field(BaseModel):
    name: str
    type: str
    repeated: bool = False
    optional: bool = False

    def render(self) -> str:
        result = ""
        if self.repeated:
            result += "repeated "
        if self.optional:
            result += "optional "
        result += f"{self.render_type()} {self.name}"
        return result

    def render_type(self) -> str:
        return self.type


class MapField(Field):
    type: Literal["map"] = "map"
    key: str
    value: str

    def render_type(self) -> str:
        return f"map<{self.key}, {self.value}>"


class Message(BaseModel):
    name: str
    fields: dict[str, Field]


class Method(BaseModel):
    name: str
    request: Message
    response: Message


class Service(BaseModel):
    package_name: str
    name: str
    methods: dict[str, Method]
    messages: dict[str, Message]
    enums: dict[str, type[enum.Enum]]
