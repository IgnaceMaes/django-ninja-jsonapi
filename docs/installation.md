# Installation

## Requirements

- Python 3.10+
- Django 4.2+
- Django Ninja 1.0+

## Install the package

```bash
uv add django-ninja-jsonapi
```

Or use another package manager:

- `pip install django-ninja-jsonapi`
- `poetry add django-ninja-jsonapi`
- `pdm add django-ninja-jsonapi`

## Verify installation

```bash
python -c "import django_ninja_jsonapi; print('ok')"
```

## Install from source (contributors)

If you want to work on this repository itself, see the development setup in `development.md`.

Quick path:

```bash
git clone https://github.com/IgnaceMaes/django-ninja-jsonapi.git
cd django-ninja-jsonapi
uv sync --dev
```
