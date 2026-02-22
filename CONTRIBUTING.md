# Contributing

## Setup

1. Fork and clone the repository.
2. Install dependencies:

```bash
uv sync --dev
```

## Development workflow

1. Create a focused branch.
2. Implement the change.
3. Add or update tests for behavior changes.
4. Run local checks:

```bash
uv run ruff format src tests
uv run ruff check src tests
uv run pytest --cov=src/django_ninja_jsonapi --cov-report=term-missing
```

5. Update docs when public behavior changes.
6. Open a pull request with:
   - clear summary
   - rationale
   - testing notes

## Scope guidelines

- Keep this project Django Ninja + Django ORM focused.
- Prefer public imports from `django_ninja_jsonapi`.
- Favor small, incremental pull requests.
