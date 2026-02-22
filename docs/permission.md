# Permission

Permission patterns are currently implemented through Django/Ninja dependencies and custom checks in view hooks.

## Recommended approach

- enforce authentication/authorization with Django middleware and Ninja auth utilities
- add operation-level guards in view configuration/dependencies
- return JSON:API exceptions (`Forbidden`, `Unauthorized`) for uniform error payloads

Dedicated permission helper abstractions may be expanded in future releases.
