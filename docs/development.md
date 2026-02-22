# Development

## Clone and setup

```bash
git clone https://github.com/IgnaceMaes/django-ninja-jsonapi.git
cd django-ninja-jsonapi
uv sync --dev
```

## Tooling

- Package/environment manager: `uv`
- Formatter/linter: `ruff`
- Test runner: `pytest` + `pytest-django`

## Common commands

```bash
uv sync
uv run ruff format src tests
uv run ruff check src tests
uv run pytest --cov=src/django_ninja_jsonapi --cov-report=term-missing
```

## Project layout

- `src/django_ninja_jsonapi/` — library code
- `tests/` — test suite
- `docs/` — documentation

## Contribution workflow

1. Add/modify code.
2. Add tests for behavior changes.
3. Run lint and tests.
4. Update docs if API/behavior changed.

## CI

GitHub Actions workflows run on pull requests and pushes to `main`:

- lint + format check
- pytest with coverage threshold
- package build validation
