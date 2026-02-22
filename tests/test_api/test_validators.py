from pydantic import BaseModel, field_validator, model_validator

from django_ninja_jsonapi.validation_utils import extract_validators


class ExampleSchema(BaseModel):
    name: str
    age: int

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("age")
    @classmethod
    def validate_age(cls, value: int) -> int:
        return value

    @model_validator(mode="after")
    def validate_model(self):
        return self


def test_extract_validators_with_include_fields():
    field_validators, model_validators = extract_validators(
        ExampleSchema,
        include_for_field_names={"name"},
    )

    assert set(field_validators) == {"validate_name"}
    assert "validate_model" in model_validators


def test_extract_validators_include_minus_exclude():
    field_validators, model_validators = extract_validators(
        ExampleSchema,
        include_for_field_names={"name", "age"},
        exclude_for_field_names={"age"},
    )

    assert set(field_validators) == {"validate_name"}
    assert "validate_model" in model_validators
