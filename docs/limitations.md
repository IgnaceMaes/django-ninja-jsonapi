# Limitations & Roadmap

## Current limitations

- Some advanced JSON:API edge cases (deep relationship workflows and full atomic semantics) need broader integration coverage.
- Sparse fieldsets on included resources are not yet filtered server-side.

## Recent additions

- End-to-end integration tests covering the full CRUD pipeline, includes, sparse fieldsets, sorting, pagination, filtering, and content negotiation.
- Content-type negotiation (415/406) per the JSON:API spec.
- Attribute key inflection (`dasherize` / `camelize`).
- Auto-generated relationship mutation routes.
- Coverage threshold raised to 75%.

## Roadmap ideas

- Expand relationship + include + atomic integration scenarios.
- Server-side sparse fieldset filtering for included resources.
- OpenAPI schema additions for JSON:API query parameters.
