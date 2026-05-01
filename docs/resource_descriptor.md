# Resource descriptor

`JsonApiResource` bundles JSON:API configuration for a single resource type, eliminating repetition of `resource_type`, `id_field`, `relationships`, and schemas across `jsonapi_body()`, `jsonapi_response()`, and `@jsonapi_resource()` calls.

## Problem

Without `JsonApiResource`, relationship config is repeated across every endpoint:

```python
RELS = {"author": {"resource_type": "people"}, "tags": {"resource_type": "tags", "many": True}}

@api.get("/articles", response=jsonapi_response(ArticleSchema, "articles", many=True, relationships=RELS))
@jsonapi_resource("articles", id_field="uuid", relationships=RELS)
def list_articles(request): ...

@api.post("/articles", response=jsonapi_response(ArticleSchema, "articles", relationships=RELS))
@jsonapi_resource("articles", id_field="uuid", relationships=RELS)
def create_article(request, body: jsonapi_body(ArticleCreateSchema, "articles", relationships=RELS)): ...

@api.patch("/articles/{id}", response=jsonapi_response(ArticleSchema, "articles", relationships=RELS))
@jsonapi_resource("articles", id_field="uuid", relationships=RELS)
def update_article(request, id: str, body: jsonapi_body(ArticleUpdateSchema, "articles", relationships=RELS)): ...
```

## Solution

Define the resource config once:

```python
from django_ninja_jsonapi import JsonApiResource

ArticleResource = JsonApiResource(
    resource_type="articles",
    id_field="uuid",
    schema=ArticleSchema,
    schema_create=ArticleCreateSchema,
    schema_update=ArticleUpdateSchema,
    relationships={
        "author": {"resource_type": "people"},
        "tags": {"resource_type": "tags", "many": True},
    },
)
```

Then use it everywhere:

```python
@api.get("/articles", response=ArticleResource.response(many=True))
@ArticleResource.decorator()
def list_articles(request):
    return jsonapi_paginate(request, Article.objects.order_by("id"))


@api.post("/articles", response=ArticleResource.response())
@ArticleResource.decorator()
def create_article(request, body: ArticleResource.body_create()):
    attrs = body.data.attributes.model_dump()
    article = Article.objects.create(**attrs)
    return article


@api.patch("/articles/{article_id}", response=ArticleResource.response())
@ArticleResource.decorator()
def update_article(request, article_id: str, body: ArticleResource.body_update()):
    article = Article.objects.get(uuid=article_id)
    apply_attributes(article, body)
    return article
```

## API

### Constructor

```python
JsonApiResource(
    resource_type: str,
    *,
    id_field: str = "id",
    schema: Type[BaseModel] | None = None,
    schema_create: Type[BaseModel] | None = None,
    schema_update: Type[BaseModel] | None = None,
    relationships: dict | None = None,
    include_jsonapi_object: bool | None = None,
    jsonapi_version: str | None = None,
)
```

### Methods

| Method | Returns | Description |
|---|---|---|
| `response(many=False)` | `Type[BaseModel]` | Builds a `jsonapi_response()` schema |
| `body(schema=None, allow_id=False)` | `Type[BaseModel]` | Builds a `jsonapi_body()` schema |
| `body_create(allow_id=False)` | `Type[BaseModel]` | Shortcut using `schema_create` |
| `body_update(allow_id=False)` | `Type[BaseModel]` | Shortcut using `schema_update` |
| `decorator(**overrides)` | Decorator | Builds a `@jsonapi_resource()` decorator |
