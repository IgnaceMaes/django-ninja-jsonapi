# Model schema

Generate Pydantic schemas from Django model definitions, reducing boilerplate for CRUD resources.

There are two approaches: **class-based** (`ModelSchema`) and **function-based** (`model_schema()`). Both produce identical results.

## Class-based — `ModelSchema`

Define a `Meta` inner class to configure field generation:

```python
from django_ninja_jsonapi import ModelSchema

class ArticleSchema(ModelSchema):
    class Meta:
        model = Article
        fields = ["uuid", "title", "body", "status", "organization_name", "created_dt"]
        resource_type = "articles"
        id_field = "uuid"

class ArticleCreateSchema(ModelSchema):
    class Meta:
        model = Article
        fields = ["title", "body", "status"]
        optional_fields = {"status"}

class ArticleUpdateSchema(ModelSchema):
    class Meta:
        model = Article
        fields = ["title", "body", "status"]
        all_optional = True
```

### Extra fields and overrides

Declare fields directly on the class body — they merge with auto-generated fields:

```python
class ArticleSchema(ModelSchema):
    full_address: str = ""          # extra field not on the model
    title: str                      # override: make required even if model has default

    class Meta:
        model = Article
        fields = ["id", "title"]
        resource_type = "articles"
```

User-declared fields always take precedence over auto-generated ones.

### `Meta` options

| Option | Type | Default | Description |
|---|---|---|---|
| `model` | Django Model | required | The Django model class |
| `fields` | `list[str]` | `None` | Field names to include. Supports DB fields and `@property` names. `None` means all concrete model fields. |
| `exclude` | `set[str]` | `None` | Field names to exclude |
| `resource_type` | `str` | `None` | JSON:API resource type. When set, attaches `JsonApiMeta` so the schema works with `NinjaJsonAPI`. |
| `id_field` | `str` | `None` | Name of the field used as the JSON:API `id`. |
| `all_optional` | `bool` | `False` | Make all fields `Optional` (for PATCH) |
| `optional_fields` | `set[str]` | `None` | Specific fields to make `Optional` |

## Function-based — `model_schema()`

```python
from django_ninja_jsonapi import model_schema

ArticleSchema = model_schema(
    Article,
    fields=["uuid", "title", "body", "status", "organization_name", "created_dt"],
    resource_type="articles",
    id_field="uuid",
)

ArticleCreateSchema = model_schema(
    Article,
    fields=["title", "body", "status"],
    optional_fields={"status"},
    name="ArticleCreateSchema",
)

ArticleUpdateSchema = model_schema(
    Article,
    fields=["title", "body", "status"],
    all_optional=True,
    name="ArticleUpdateSchema",
)
```

When using `resource_type`, a `JsonApiMeta` is attached to the generated schema automatically.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `model` | Django Model | required | The Django model class |
| `fields` | `list[str]` | `None` | Field names to include. Supports DB fields and `@property` names. If `None`, all concrete fields are included. |
| `exclude` | `set[str]` | `None` | Field names to exclude |
| `id_field` | `str` | `None` | Name of the field used as the JSON:API `id`. Passed to `JsonApiMeta` when `resource_type` is set. |
| `optional_fields` | `set[str]` | `None` | Fields to mark as `Optional` |
| `all_optional` | `bool` | `False` | Make all fields `Optional` (for PATCH) |
| `name` | `str` | `None` | Custom schema name (default: `{Model}Schema`) |
| `extra_fields` | `dict` | `None` | Additional Pydantic field definitions |
| `resource_type` | `str` | `None` | JSON:API resource type (e.g. `"articles"`). When set, attaches `JsonApiMeta` so the schema works with `NinjaJsonAPI`. |

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
from django_ninja_jsonapi import NinjaJsonAPI, ModelSchema, apply_attributes, jsonapi_paginate


# Schemas
class ArticleSchema(ModelSchema):
    class Meta:
        model = Article
        fields = ["uuid", "title", "body", "status", "created_dt"]
        resource_type = "articles"
        id_field = "uuid"


class ArticleCreateSchema(ModelSchema):
    class Meta:
        model = Article
        fields = ["title", "body"]


class ArticleUpdateSchema(ModelSchema):
    class Meta:
        model = Article
        fields = ["title", "body", "status"]
        all_optional = True


# API
api = NinjaJsonAPI()


@api.get("/articles", response=list[ArticleSchema])
def list_articles(request):
    return jsonapi_paginate(request, Article.objects.order_by("id"))


@api.post("/articles", response={201: ArticleSchema})
def create_article(request, body: ArticleCreateSchema):
    article = Article.objects.create(**body.model_dump())
    return article


@api.patch("/articles/{article_id}", response=ArticleSchema)
def update_article(request, article_id: str, body: ArticleUpdateSchema):
    article = Article.objects.get(uuid=article_id)
    apply_attributes(article, body)
    return article
```
