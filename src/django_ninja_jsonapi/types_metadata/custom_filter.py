from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CustomFilter:
    op: str

    def apply(self, field_name: str, value: Any) -> tuple[str, Any]:
        return field_name, value
