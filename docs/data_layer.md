# Data layer

The data layer is the CRUD boundary between view orchestration and persistence.

## Responsibilities

- resource create/read/update/delete
- relationship linkage operations
- filter/sort/pagination translation

## Current implementation

- Django ORM is the only supported persistence backend.
- Query translation is implemented in `data_layers/django_orm`.

## Extension path

You can subclass or replace data-layer classes when custom storage behavior is needed.
