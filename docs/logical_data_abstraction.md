# Logical data abstraction

Resource schemas are your API contract and do not need to mirror Django models 1:1.

## Common transformations

- hide internal model fields
- expose computed fields
- rename model fields for API clarity
- expose relationships under business-friendly names

This abstraction lets you evolve storage internals without breaking public API shape.

## Example

```python
from pydantic import BaseModel, computed_field


class CustomerSchema(BaseModel):
	id: int
	name: str
	email: str

	@computed_field
	@property
	def display_name(self) -> str:
		return f"{self.name} <{self.email}>"
```

If your model also has `password`, keep it out of the schema so it is never exposed.
