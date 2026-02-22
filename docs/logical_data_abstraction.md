# Logical data abstraction

Resource schemas are your API contract and do not need to mirror Django models 1:1.

## Common transformations

- hide internal model fields
- expose computed fields
- rename model fields for API clarity
- expose relationships under business-friendly names

This abstraction lets you evolve storage internals without breaking public API shape.
