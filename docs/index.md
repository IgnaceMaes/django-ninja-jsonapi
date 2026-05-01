# django-ninja-jsonapi

`django-ninja-jsonapi` is a Django Ninja extension for building JSON:API-style REST APIs.

## Main concepts

- **JSON:API semantics**: resource objects, relationships, includes, sparse fieldsets, filtering, sorting, pagination, and standardized errors.
- **Transparent wrapping**: `NinjaJsonAPI` automatically wraps plain Pydantic responses in JSON:API documents and unwraps JSON:API request bodies.
- **Logical data abstraction**: schemas can expose a resource view that differs from raw model structure.

## Features

- Transparent JSON:API response wrapping and request body unwrapping
- Auto-detected relationships from schema type hints
- Query parsing for `filter`, `sort`, `include`, `fields`, and `page`
- JSON:API error envelopes
- Content-type negotiation (415/406)

## Documentation

### Getting started

- [Getting started](getting-started.md)
- [Installation](installation.md)
- [Quickstart](quickstart.md)
- [Transparent JSON:API](transparent_jsonapi.md)

### Usage

- [Usage overview](usage.md)
- [Configuration](configuration.md)
- [Logical data abstraction](logical_data_abstraction.md)
- [Model schema](model_schema.md)
- [Include related objects](include_related_objects.md)
- [Include many-to-many](include_many_to_many.md)
- [Filtering](filtering.md)
- [Sorting](sorting.md)
- [Sparse fieldsets](sparse_fieldsets.md)
- [Pagination](pagination.md)
- [Content negotiation](content_negotiation.md)
- [Inflection](inflection.md)
- [Errors](errors.md)

### Examples

- [Examples overview](examples.md)
- [API filtering example](api_filtering_example.md)

### Reference and project

- [API reference](api-reference.md)
- [Development](development.md)
- [Testing](testing.md)
- [Limitations & roadmap](limitations.md)
