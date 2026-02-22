# Updated includes example

This example combines relationship updates with `include` to return expanded payloads in one call.

## Example flow

1. Update resource attributes and relationships.
2. Request related resources using `include`.
3. Receive primary `data` plus `included` resources.

```http
PATCH /users/1?include=computers
```

Use this pattern when clients need immediate post-update relationship context.
