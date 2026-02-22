"""Enum mixin module."""

from enum import Enum


class MixinEnum(Enum):
    """Extension over enum class from standard library."""

    @classmethod
    def names(cls):
        """Get all field names."""
        return ",".join(field.name for field in cls)

    @classmethod
    def values(cls):
        """Get all values from Enum."""
        return [value for _, value in cls._member_map_.items()]

    @classmethod
    def keys(cls):
        """Get all field keys from Enum."""
        return [key for key, _ in cls._member_map_.items()]

    @classmethod
    def inverse(cls):
        """Return all inverted items sequence."""
        return {value: key for key, value in cls._member_map_.items()}

    @classmethod
    def value_to_enum(cls, value):
        """Convert value to enum."""
        val_to_enum = {value.value: value for _, value in cls._member_map_.items()}
        return val_to_enum.get(value)
