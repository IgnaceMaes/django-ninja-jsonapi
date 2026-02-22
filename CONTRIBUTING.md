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

## Local checks

Run these before opening a pull request:

```bash
uv run ruff format src tests
uv run ruff check src tests
uv run pytest --cov=src/django_ninja_jsonapi --cov-report=term-missing
```

## Test coverage focus

Current tests cover:

- Application builder initialization and route registration behavior
- Query-string parsing behavior
- Django ORM query-building mapping (`filter`/`sort` translation)
- Exception handler response shape

## Release process (maintainers)

Releases are automated with GitHub Actions:

1. Merge conventional-commit PRs into `main`.
2. `Release Please` opens or updates a release PR with version bump + changelog updates.
3. Merge the release PR to create a GitHub Release.
4. `Publish to PyPI` runs on `release: published` and uploads the built package to PyPI.

Workflows:

- `.github/workflows/release-please.yml`
- `.github/workflows/publish.yml`

Required repository secrets:

- `REPO_ADMIN_TOKEN` (used by Release Please)
- `PYPI_API_TOKEN` (used for PyPI publishing)

## Scope guidelines

- Keep this project Django Ninja + Django ORM focused.
- Prefer public imports from `django_ninja_jsonapi`.
- Favor small, incremental pull requests.
