# Client-generated ID

JSON:API allows clients to send IDs during create requests in some workflows.

## Guidance

- Prefer server-generated IDs for most Django model setups.
- Enable client IDs only when your domain requires externally assigned identifiers.
- Validate uniqueness and ownership constraints at the data-layer boundary.

If enabled, treat client-provided IDs as untrusted input and enforce strict validation.
