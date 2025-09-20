import enum
import inspect
from typing import Annotated, Any, Iterable, Union, UnionType, get_origin

from pydantic import BaseModel


class TypeProcessor:
    type_: type

    def process(self, data: Any, annotation: type) -> Any:
        return data


class DataProcessor:
    def __init__(self, *type_processors: TypeProcessor):
        self._type_processors = type_processors

    def __call__(self, data: dict[str, Any], model: type[BaseModel], **extra) -> dict[str, Any]:
        return self.process_model(data=data, annotation=model, **extra)

    def process(self, data: Any, annotation: type, **extra) -> Any:
        if (origin := get_origin(annotation)) is not None:
            if origin in (Annotated, Union, UnionType):
                return self.process(data=data, annotation=annotation.__args__[0], **extra)
            if issubclass(origin, dict):
                return self.process_dict(data=data, annotation=annotation, **extra)
            if issubclass(origin, Iterable):
                return self.process_list(data=data, annotation=annotation, **extra)
        if inspect.isclass(annotation):
            if issubclass(annotation, BaseModel):
                return self.process_model(data=data, annotation=annotation, **extra)
            for type_processor in self._type_processors:
                if issubclass(annotation, type_processor.type_):
                    return type_processor.process(data=data, annotation=annotation)
        return data

    def process_dict(self, data: dict, annotation: type, **extra) -> dict:
        if not hasattr(annotation, "__args__") or len(annotation.__args__) != 2:
            return data

        key_annotation, value_annotation = annotation.__args__
        result_dict = {}
        for key, value in data.items():
            result_key = self.process(data=key, annotation=key_annotation, **extra)
            result_value = self.process(data=value, annotation=value_annotation, **extra)
            result_dict[result_key] = result_value
        return result_dict

    def process_list(self, data: Iterable, annotation: type, **extra) -> list:
        if not hasattr(annotation, "__args__"):
            return data

        item_annotation = annotation.__args__[0]
        return [
            self.process(data=item, annotation=item_annotation, **extra)
            for item in data
        ]

    def process_model(
            self,
            data: dict[str, Any],
            annotation: type[BaseModel],
            **extra,
    ) -> dict[str, Any]:
        result_data = data.copy()
        for key, value in data.items():
            result_data[key] = self.process(
                data=value,
                annotation=annotation.model_fields[key].annotation,
            )
        return result_data


class EnumNameByValueTypeProcessor(TypeProcessor):
    type_ = enum.Enum

    def process(self, data: Any, annotation: type[enum.Enum]) -> enum.Enum:
        return annotation(data).name


class EnumByValueTypeProcessor(TypeProcessor):
    type_ = enum.Enum

    def process(self, data: Any, annotation: type[enum.Enum]) -> enum.Enum:
        return annotation(data)


class EnumByNameTypeProcessor(TypeProcessor):
    type_ = enum.Enum

    def process(self, data: str, annotation: type[enum.Enum]) -> enum.Enum:
        return annotation[data]
