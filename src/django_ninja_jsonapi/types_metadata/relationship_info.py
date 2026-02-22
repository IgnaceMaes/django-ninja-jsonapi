from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class RelationshipInfo:
    resource_type: str
    many: bool = False
    resource_id_example: str = "1"
    id_field_name: str = "id"
    model_field_name: Optional[str] = None
