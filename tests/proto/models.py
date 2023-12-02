import pathlib
import uuid
from typing import Annotated, Iterable, Optional

from pydantic import (
    BaseModel,
    EmailStr,
    NegativeInt,
    NonNegativeInt,
    NonPositiveInt,
    PositiveInt,
    confloat,
    conint,
)

from fast_grpc.proto.enums import TypeEnum
from fast_grpc.proto.models import Field


class RootModel(BaseModel):
    one: int
    two: Annotated[NonPositiveInt | None, "any annotation"]
    three: Optional[Optional[NegativeInt]]
    four: NonNegativeInt | None | None
    five: PositiveInt
    six: tuple[conint(ge=-10, le=10)]
    seven: set[float]
    eight: confloat(ge=0, le=1)
    nine: bool
    ten: str
    eleven: EmailStr
    twelve: uuid.UUID
    thirteen: dict[pathlib.Path, int]
    fourteen: bytes
    fifteen: dict[int, bool]


ROOT_FIELDS = {
    "one": Field(name="one", type=TypeEnum.INT64),
    "two": Field(name="two", type=TypeEnum.INT64),
    "three": Field(name="three", type=TypeEnum.INT64),
    "four": Field(name="four", type=TypeEnum.INT64),
    "five": Field(name="five", type=TypeEnum.INT64),
    "six": Field(name="six", type=TypeEnum.INT64, repeated=True),
    "seven": Field(name="seven", type=TypeEnum.DOUBLE, repeated=True),
    "eight": Field(name="eight", type=TypeEnum.DOUBLE),
    "nine": Field(name="nine", type=TypeEnum.BOOL),
    "ten": Field(name="ten", type=TypeEnum.STRING),
    "eleven": Field(name="eleven", type=TypeEnum.STRING),
    "twelve": Field(name="twelve", type=TypeEnum.STRING),
    "thirteen": Field(name="thirteen", type=TypeEnum.MAP, map_key=TypeEnum.STRING,
                      map_value=TypeEnum.INT64),
    "fourteen": Field(name="fourteen", type=TypeEnum.BYTES),
    "fifteen": Field(name="fifteen", type=TypeEnum.MAP, map_key=TypeEnum.INT64,
                     map_value=TypeEnum.BOOL),
}


class FirstModel(BaseModel):
    root: list[RootModel]


FIRST_FIELDS = {
    "root": Field(name="root", type="RootModel", repeated=True),
}


class SecondModel(BaseModel):
    first: FirstModel


SECOND_FIELDS = {
    "first": Field(name="first", type="FirstModel"),
}


class ThirdModel(RootModel):
    sixteen: int


THIRD_FIELDS = {
    **ROOT_FIELDS,
    "sixteen": Field(name="sixteen", type=TypeEnum.INT64),
}


class FourthModel(RootModel):
    another: dict[conint(ge=2, le=5), FirstModel]
    one_more: Iterable[SecondModel]


FOURTH_FIELDS = {
    **ROOT_FIELDS,
    "another": Field(name="another", type=TypeEnum.MAP, map_key=TypeEnum.INT64,
                     map_value="FirstModel"),
    "one_more": Field(name="one_more", type="SecondModel", repeated=True),
}
