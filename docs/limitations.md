# Limitations & Roadmap

## Current limitations

- Sparse fieldsets on included resources are not yet filtered server-side.

## Recent additions

- Content-type negotiation (415/406) per the JSON:API spec.
- Attribute key inflection (`dasherize` / `camelize`).
- Transparent JSON:API wrapping via `NinjaJsonAPI`.
- Coverage threshold raised to 75%.

## Roadmap ideas

- Server-side sparse fieldset filtering for included resources.
- OpenAPI schema additions for JSON:API query parameters.
