"""Base enum module."""

from django_ninja_jsonapi.data_layers.fields.mixins import MixinEnum


class Enum(MixinEnum):
    """
    Base enum class.

    All used non-integer enumerations must inherit from this class.
    """
