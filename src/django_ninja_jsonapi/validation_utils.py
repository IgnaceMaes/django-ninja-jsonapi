from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Optional, Type

from pydantic import BaseModel, field_validator, model_validator
from pydantic._internal._decorators import PydanticDescriptorProxy

if TYPE_CHECKING:
    # noinspection PyProtectedMember
    from pydantic._internal._decorators import DecoratorInfos


def extract_validators(
    model: Type[BaseModel],
    include_for_field_names: Optional[set[str]] = None,
    exclude_for_field_names: Optional[set[str]] = None,
) -> tuple[dict[str, Callable], dict[str, PydanticDescriptorProxy]]:
    validators: DecoratorInfos = model.__pydantic_decorators__

    exclude_for_field_names = exclude_for_field_names or set()
    if include_for_field_names and exclude_for_field_names:
        include_for_field_names = include_for_field_names.difference(
            exclude_for_field_names,
        )

    field_validators, model_validators = {}, {}

    # field validators
    for name, validator in validators.field_validators.items():
        for field_name in validator.info.fields:
            # exclude
            if field_name in exclude_for_field_names:
                continue
            # or include
            if include_for_field_names and field_name not in include_for_field_names:
                continue
            validator_config = field_validator(field_name, mode=validator.info.mode)

            func = validator.func.__func__ if hasattr(validator.func, "__func__") else validator.func

            field_validators[name] = validator_config(func)

    # model validators
    for name, validator in validators.model_validators.items():
        validator_config = model_validator(mode=validator.info.mode)

        func = validator.func.__func__ if hasattr(validator.func, "__func__") else validator.func

        model_validators[name] = validator_config(func)

    return field_validators, model_validators
