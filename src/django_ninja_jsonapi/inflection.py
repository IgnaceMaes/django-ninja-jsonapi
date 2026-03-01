"""Attribute-key inflection for JSON:API member names.

Provides ``dasherize`` and ``camelize`` transformers that can be activated
via the Django ``NINJA_JSONAPI`` setting::

    NINJA_JSONAPI = {
        "INFLECTION": "dasherize",   # or "camelize", or None (default)
    }

When enabled the transformer is applied to serialised attribute keys so that
Python-side ``first_name`` becomes ``first-name`` (dasherize) or
``firstName`` (camelize) in the JSON:API document.  The inverse function
(``underscore``) is exposed for use on incoming payloads.
"""

from __future__ import annotations

import re
from typing import Callable, Optional

from django.conf import settings

_UPPER_FOLLOWED_BY_LOWER = re.compile(r"([A-Z]+)([A-Z][a-z])")
_LOWER_OR_DIGIT_FOLLOWED_BY_UPPER = re.compile(r"([a-z\d])([A-Z])")


# ---------------------------------------------------------------------------
# Core transformers
# ---------------------------------------------------------------------------


def dasherize(value: str) -> str:
    """Convert underscores to hyphens.  ``first_name`` → ``first-name``."""
    return value.replace("_", "-")


def camelize(value: str) -> str:
    """Convert to lower-camelCase.  ``first_name`` → ``firstName``."""
    parts = value.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])


def underscore(value: str) -> str:
    """Convert dasherized or camelCase back to underscored.

    ``first-name`` → ``first_name``
    ``firstName``  → ``first_name``
    """
    value = value.replace("-", "_")
    value = _UPPER_FOLLOWED_BY_LOWER.sub(r"\1_\2", value)
    value = _LOWER_OR_DIGIT_FOLLOWED_BY_UPPER.sub(r"\1_\2", value)
    return value.lower()


# ---------------------------------------------------------------------------
# Dict-key helpers
# ---------------------------------------------------------------------------


def format_keys(data: dict, formatter: Callable[[str], str]) -> dict:
    """Return a *shallow* copy of *data* with every key passed through *formatter*."""
    return {formatter(key): value for key, value in data.items()}


def unformat_keys(data: dict) -> dict:
    """Reverse inflection on dict keys (always uses ``underscore``)."""
    return {underscore(key): value for key, value in data.items()}


# ---------------------------------------------------------------------------
# Configuration reader
# ---------------------------------------------------------------------------

_FORMATTERS: dict[str, Callable[[str], str]] = {
    "dasherize": dasherize,
    "camelize": camelize,
}


def get_formatter() -> Optional[Callable[[str], str]]:
    """Return the active inflection formatter, or ``None`` if disabled."""
    ninja_jsonapi = getattr(settings, "NINJA_JSONAPI", {})
    name = ninja_jsonapi.get("INFLECTION")
    if name is None:
        return None
    formatter = _FORMATTERS.get(name)
    if formatter is None:
        msg = (
            f"NINJA_JSONAPI['INFLECTION'] = {name!r} is not a recognised inflection. "
            f"Choose from: {', '.join(sorted(_FORMATTERS))} or None."
        )
        raise ValueError(msg)
    return formatter
