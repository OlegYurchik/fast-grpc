import enum
import uuid


class TypeEnum(str, enum.Enum):
    DOUBLE = "double"
    FLOAT = "float"
    INT32 = "int32"
    INT64 = "int64"
    UINT32 = "uint32"
    UINT64 = "uint64"
    SINT32 = "sint32"
    SINT64 = "sint64"
    FIXED32 = "fixed32"
    FIXED64 = "fixed64"
    SFIXED32 = "sfixed32"
    SFIXED64 = "sfixed64"
    BOOL = "bool"
    STRING = "string"
    BYTES = "bytes"


TYPE_MAPPING = {
    int: TypeEnum.INT64,
    float: TypeEnum.FLOAT,
    bool: TypeEnum.BOOL,
    str: TypeEnum.STRING,
    bytes: TypeEnum.BYTES,
    uuid.UUID: TypeEnum.STRING,
}
