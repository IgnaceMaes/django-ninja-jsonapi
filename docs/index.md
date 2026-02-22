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

## User guide

- [Installation](installation.md)
- [Minimal API (head)](minimal_api_head.md)
- [Minimal API example](minimal_api_example.md)
- [API filtering example](api_filtering_example.md)
- [Limited methods example](api_limited_methods_example.md)
- [Quickstart](quickstart.md)
- [Routing](routing.md)
- [Atomic operations](atomic_operations.md)
- [View dependencies](view_dependencies.md)
- [Filtering](filtering.md)
- [Updated includes example](updated_includes_example.md)
- [Include related objects](include_related_objects.md)
- [Include many-to-many](include_many_to_many.md)
- [Custom filtering](custom_sql_filtering.md)
- [Client-generated ID](client_generated_id.md)
- [Logical data abstraction](logical_data_abstraction.md)
- [Data layer](data_layer.md)
- [Relationships](relationships.md)
- [Configuration](configuration.md)
- [Sparse fieldsets](sparse_fieldsets.md)
- [Pagination](pagination.md)
- [Sorting](sorting.md)
- [Errors](errors.md)
- [Permission](permission.md)
- [OAuth](oauth.md)
- [fastapi-jsonapi topic alias](fastapi-jsonapi.md)
- [django-ninja-jsonapi package](django-ninja-jsonapi.md)

## Project docs

- [API reference](api-reference.md)
- [Development](development.md)
- [Testing](testing.md)
- [Limitations & roadmap](limitations.md)
