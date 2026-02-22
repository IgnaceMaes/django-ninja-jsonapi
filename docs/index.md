# django-ninja-jsonapi

`django-ninja-jsonapi` is a Django Ninja extension for building JSON:API-style REST APIs with a Django ORM data layer.

## Main concepts

- **JSON:API semantics**: resource objects, relationships, includes, sparse fieldsets, filtering, sorting, pagination, and standardized errors.
- **Logical data abstraction**: schemas can expose a resource view that differs from raw model structure.
- **Data layer separation**: request parsing and endpoint orchestration are separated from ORM read/write behavior.

## Features

- Resource registration and CRUD route generation
- Relationship and relationship-link routes
- Query parsing for `filter`, `sort`, `include`, `fields`, and `page`
- JSON:API error envelopes
- Atomic operations endpoint wiring (`/operations`)

## Documentation

### Getting started

- [Getting started](getting-started.md)
- [Installation](installation.md)
- [Quickstart](quickstart.md)

### Usage

- [Usage overview](usage.md)
- [Routing](routing.md)
- [Configuration](configuration.md)
- [Relationships](relationships.md)
- [Filtering](filtering.md)
- [Sorting](sorting.md)
- [Pagination](pagination.md)
- [Errors](errors.md)

### Examples

- [Examples overview](examples.md)
- [Minimal API (head)](minimal_api_head.md)
- [Minimal API example](minimal_api_example.md)
- [API filtering example](api_filtering_example.md)
- [Limited methods example](api_limited_methods_example.md)

### Reference and project

- [API reference](api-reference.md)
- [Development](development.md)
- [Testing](testing.md)
- [Limitations & roadmap](limitations.md)
