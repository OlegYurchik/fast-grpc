from pydantic import BaseModel, model_validator

from .enums import TypeEnum


class Field(BaseModel):
    name: str
    type: str
    repeated: bool = False
    map_key: str | None = None
    map_value: str | None = None

    @model_validator(mode="after")
    def root_validator(self):
        if self.type is TypeEnum.MAP:
            if self.repeated:
                raise ValueError("Field 'repeated' cannot be True, when protobuf type is 'map'")
            if self.map_key is None:
                raise ValueError("Field 'map_key' must be set, when protobuf type is 'map'")
            if self.map_value is None:
                raise ValueError("Field 'map_value' must be set, when protobuf type is 'map'")

        return self


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
