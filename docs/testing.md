# Testing

The project uses `pytest` with `pytest-django`.

## Run all tests

```bash
uv run pytest
```

## Current coverage areas

- ApplicationBuilder initialization and route registration
- Querystring parsing (`filter`, `sort`, `include`, `pagination`)
- Django ORM query-building filter/sort mapping
- Exception handler response envelope

## Writing new tests

- Prefer small focused unit tests for parsing/translation logic.
- Add integration tests when route behavior changes.
- Keep test settings in `tests/settings.py`.
