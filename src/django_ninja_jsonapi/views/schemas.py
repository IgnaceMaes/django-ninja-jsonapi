from typing import Callable, Coroutine, Optional, Type, Union

from pydantic import BaseModel, ConfigDict


class OperationConfig(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    dependencies: Optional[Type[BaseModel]] = None
    prepare_data_layer_kwargs: Optional[Union[Callable, Coroutine]] = None

    @property
    def handler(self) -> Optional[Union[Callable, Coroutine]]:
        return self.prepare_data_layer_kwargs


class RelationshipRequestInfo(BaseModel):
    parent_obj_id: str
    parent_resource_type: str
    relationship_name: str
