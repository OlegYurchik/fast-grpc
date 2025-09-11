import pathlib
import uuid
from typing import Annotated, get_origin

from pydantic import EmailStr, NegativeInt, NonNegativeInt, NonPositiveInt, PositiveInt


TYPE_MAPPING = {
    int: "int64",
    NonPositiveInt: "int64",
    NegativeInt: "int64",
    NonNegativeInt: "int64",
    PositiveInt: "int64",
    float: "double",
    bool: "bool",
    str: "string",
    EmailStr: "string",
    uuid.UUID: "string",
    pathlib.Path: "string",
    bytes: "bytes",
}

ORIGIN_TYPES_MAPPING = {
    python_type_: type_
    for python_type_, type_ in TYPE_MAPPING.items()
    if get_origin(python_type_) not in (Annotated,)
}
