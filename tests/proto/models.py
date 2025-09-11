import enum
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

from fast_grpc.proto.models import Field, MapField


class RootModelEnum(enum.Enum):
    OPTION_1 = "option_1"
    OPTION_2 = 2.0
    OPTION_3 = 3


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
    sixteen: RootModelEnum


ROOT_FIELDS = {
    "one": Field(name="one", type="int64"),
    "two": Field(name="two", type="int64", optional=True),
    "three": Field(name="three", type="int64", optional=True),
    "four": Field(name="four", type="int64", optional=True),
    "five": Field(name="five", type="int64"),
    "six": Field(name="six", type="int64", repeated=True),
    "seven": Field(name="seven", type="double", repeated=True),
    "eight": Field(name="eight", type="double"),
    "nine": Field(name="nine", type="bool"),
    "ten": Field(name="ten", type="string"),
    "eleven": Field(name="eleven", type="string"),
    "twelve": Field(name="twelve", type="string"),
    "thirteen": MapField(name="thirteen", key="string", value="int64"),
    "fourteen": Field(name="fourteen", type="bytes"),
    "fifteen": MapField(name="fifteen", key="int64", value="bool"),
    "sixteen": Field(name="sixteen", type=RootModelEnum.__name__),
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
    seventeen: int


THIRD_FIELDS = {
    **ROOT_FIELDS,
    "seventeen": Field(name="seventeen", type="int64"),
}


class FourthModel(RootModel):
    another: dict[conint(ge=2, le=5), FirstModel]
    one_more: Iterable[SecondModel]


FOURTH_FIELDS = {
    **ROOT_FIELDS,
    "another": MapField(name="another", type="map", key="int64",
                        value="FirstModel"),
    "one_more": Field(name="one_more", type="SecondModel", repeated=True),
}
