# Model schema factory

`model_schema()` generates Pydantic schemas from Django model definitions, reducing boilerplate for simple CRUD resources.

## Problem

For every resource, you typically need 3 schemas (read, create, update), each manually listing fields and keeping them in sync with the model.

## Solution

```python
from django_ninja_jsonapi import model_schema

# Read schema — includes computed properties
ArticleSchema = model_schema(
    Article,
    fields=["uuid", "title", "body", "status", "organization_name", "created_dt"],
)

# Create schema — only writable fields
ArticleCreateSchema = model_schema(
    Article,
    fields=["title", "body", "status"],
    optional_fields={"status"},  # has a default
)

# Update schema — all fields optional (PATCH semantics)
ArticleUpdateSchema = model_schema(
    Article,
    fields=["title", "body", "status"],
    all_optional=True,
)
```

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `model` | Django Model | required | The Django model class |
| `fields` | `list[str]` | `None` | Field names to include. Supports DB fields and `@property` names. If `None`, all concrete fields are included. |
| `exclude` | `set[str]` | `None` | Field names to exclude |
| `id_field` | `str` | `None` | Reserved for future use |
| `optional_fields` | `set[str]` | `None` | Fields to mark as `Optional` |
| `all_optional` | `bool` | `False` | Make all fields `Optional` (for PATCH) |
| `name` | `str` | `None` | Custom schema name (default: `{Model}Schema`) |
| `extra_fields` | `dict` | `None` | Additional Pydantic field definitions |

## Features

### Automatic type mapping

Django field types are automatically mapped to Python types:

| Django Field | Python Type |
|---|---|
| `CharField`, `TextField`, `EmailField`, `URLField`, `SlugField` | `str` |
| `IntegerField`, `BigIntegerField`, `SmallIntegerField`, `AutoField` | `int` |
| `FloatField` | `float` |
| `BooleanField` | `bool` |
| `DateField` | `datetime.date` |
| `DateTimeField` | `datetime.datetime` |
| `UUIDField` | `uuid.UUID` |
| `DecimalField` | `Decimal` |
| `JSONField` | `Any` |
| `ForeignKey` | type of related model's PK |

### Nullable and default fields

Fields with `null=True` or a `default=` value are automatically made `Optional`.

### `@property` fields

You can include `@property` names in the `fields` list:

```python
class Article(models.Model):
    title = models.CharField(max_length=200)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)

    @property
    def organization_name(self) -> str:
        return self.organization.name


ArticleSchema = model_schema(
    Article,
    fields=["id", "title", "organization_name"],
)
```

### `from_attributes` enabled

All generated schemas have `ConfigDict(from_attributes=True)`, so they work with `schema.model_validate(instance, from_attributes=True)` and the renderer's schema-aware coercion.

### Extra fields

Add fields not on the model:

```python
ArticleSchema = model_schema(
    Article,
    fields=["title"],
    extra_fields={"custom_score": (float, 0.0)},
)
```

## Full example

```python
from django_ninja_jsonapi import JsonApiResource, model_schema, apply_attributes, setup_jsonapi

# Schemas
ArticleSchema = model_schema(Article, fields=["uuid", "title", "body", "status", "created_dt"])
ArticleCreateSchema = model_schema(Article, fields=["title", "body"], name="ArticleCreateSchema")
ArticleUpdateSchema = model_schema(Article, fields=["title", "body", "status"], all_optional=True, name="ArticleUpdateSchema")

# Resource
ArticleResource = JsonApiResource(
    resource_type="articles",
    id_field="uuid",
    schema=ArticleSchema,
    schema_create=ArticleCreateSchema,
    schema_update=ArticleUpdateSchema,
)

# Endpoints
@api.get("/articles", response=ArticleResource.response(many=True))
@ArticleResource.decorator()
def list_articles(request):
    return jsonapi_paginate(request, Article.objects.order_by("id"))

@api.post("/articles", response=ArticleResource.response())
@ArticleResource.decorator()
def create_article(request, body: ArticleResource.body_create()):
    article = Article.objects.create(**body.data.attributes.model_dump())
    return article

@api.patch("/articles/{article_id}", response=ArticleResource.response())
@ArticleResource.decorator()
def update_article(request, article_id: str, body: ArticleResource.body_update()):
    article = Article.objects.get(uuid=article_id)
    apply_attributes(article, body)
    return article
```
