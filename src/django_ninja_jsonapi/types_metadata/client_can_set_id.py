from dataclasses import dataclass
from typing import Any, Callable, Optional


@dataclass(frozen=True)
class ClientCanSetId:
    cast_type: Optional[Callable[[Any], Any]] = None
