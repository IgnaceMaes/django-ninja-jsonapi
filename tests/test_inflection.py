"""Tests for inflection module (dasherize/camelize attribute key transformation)."""

from __future__ import annotations

import pytest
from django.test.utils import override_settings

from django_ninja_jsonapi.inflection import (
    camelize,
    dasherize,
    format_keys,
    get_formatter,
    underscore,
    unformat_keys,
)

# ---------------------------------------------------------------------------
# Core transformers
# ---------------------------------------------------------------------------


class TestDasherize:
    def test_underscored(self):
        assert dasherize("first_name") == "first-name"

    def test_already_dasherized(self):
        assert dasherize("first-name") == "first-name"

    def test_single_word(self):
        assert dasherize("name") == "name"

    def test_multiple_underscores(self):
        assert dasherize("long_field_name") == "long-field-name"


class TestCamelize:
    def test_underscored(self):
        assert camelize("first_name") == "firstName"

    def test_single_word(self):
        assert camelize("name") == "name"

    def test_multiple_underscores(self):
        assert camelize("long_field_name") == "longFieldName"


class TestUnderscore:
    def test_dasherized(self):
        assert underscore("first-name") == "first_name"

    def test_camel_case(self):
        assert underscore("firstName") == "first_name"

    def test_single_word(self):
        assert underscore("name") == "name"

    def test_already_underscored(self):
        assert underscore("first_name") == "first_name"

    def test_upper_camel(self):
        assert underscore("FirstName") == "first_name"

    def test_acronym(self):
        assert underscore("HTMLParser") == "html_parser"


# ---------------------------------------------------------------------------
# Dict-key helpers
# ---------------------------------------------------------------------------


class TestFormatKeys:
    def test_dasherize_keys(self):
        data = {"first_name": "Alice", "last_name": "Bob"}
        result = format_keys(data, dasherize)
        assert result == {"first-name": "Alice", "last-name": "Bob"}

    def test_camelize_keys(self):
        data = {"first_name": "Alice"}
        result = format_keys(data, camelize)
        assert result == {"firstName": "Alice"}

    def test_no_side_effect(self):
        original = {"first_name": "Alice"}
        format_keys(original, dasherize)
        assert original == {"first_name": "Alice"}


class TestUnformatKeys:
    def test_dasherized(self):
        data = {"first-name": "Alice", "last-name": "Bob"}
        result = unformat_keys(data)
        assert result == {"first_name": "Alice", "last_name": "Bob"}

    def test_camelized(self):
        data = {"firstName": "Alice"}
        result = unformat_keys(data)
        assert result == {"first_name": "Alice"}


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


class TestGetFormatter:
    @override_settings(NINJA_JSONAPI={})
    def test_no_inflection_setting(self):
        assert get_formatter() is None

    @override_settings(NINJA_JSONAPI={"INFLECTION": None})
    def test_inflection_explicitly_none(self):
        assert get_formatter() is None

    @override_settings(NINJA_JSONAPI={"INFLECTION": "dasherize"})
    def test_dasherize_setting(self):
        formatter = get_formatter()
        assert formatter is not None
        assert formatter("first_name") == "first-name"

    @override_settings(NINJA_JSONAPI={"INFLECTION": "camelize"})
    def test_camelize_setting(self):
        formatter = get_formatter()
        assert formatter is not None
        assert formatter("first_name") == "firstName"

    @override_settings(NINJA_JSONAPI={"INFLECTION": "invalid"})
    def test_invalid_inflection_raises(self):
        with pytest.raises(ValueError, match="not a recognised inflection"):
            get_formatter()
