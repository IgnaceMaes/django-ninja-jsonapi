from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CustomSort:
    descending: bool = False

    def apply(self, field_name: str) -> str:
        return f"-{field_name}" if self.descending else field_name
