# Transparent JSON:API

`NinjaJsonAPI` is a drop-in `NinjaAPI` subclass that makes JSON:API formatting invisible. Your view functions look exactly like plain Django Ninja views — the library handles wrapping responses and unwrapping request bodies automatically.

## Quick example

```python
from django_ninja_jsonapi import NinjaJsonAPI

api = NinjaJsonAPI()

@api.post("/articles", response={201: ArticleSchema})
def create_article(request, body: ArticleCreateSchema):
    article = Article.objects.create(**body.model_dump())
    return 201, article
```

Plain Pydantic schemas in, JSON:API documents out. No decorators, no body wrappers, no `.data.attributes`.

## Setup

Replace `NinjaAPI` with `NinjaJsonAPI`:

```python
from django_ninja_jsonapi import NinjaJsonAPI

api = NinjaJsonAPI(
    urls_namespace="my-api",
    # all standard NinjaAPI kwargs work: auth, title, version, etc.
)
```

`NinjaJsonAPI` automatically:

- Sets the `JSONAPIRenderer`
- Registers JSON:API exception handlers for `HTTPException` and `ObjectDoesNotExist`
- Wraps `response=` schemas in JSON:API document structure (for OpenAPI docs)
- Unwraps incoming JSON:API request bodies so views receive plain schemas
- Injects JSON:API resource config on each request

## Schema configuration with `JsonApiMeta`

Attach a `JsonApiMeta` to your Pydantic schemas to declare JSON:API resource type and ID field:

```python
from typing import ClassVar
from pydantic import BaseModel, ConfigDict
from django_ninja_jsonapi import JsonApiMeta

class ArticleSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: str
    title: str
    body: str
    author: UserSchema | None = None
    tags: list[TagSchema] = []

    jsonapi_meta: ClassVar[JsonApiMeta] = JsonApiMeta(
        resource_type="articles",
        id_field="uuid",
    )
```

Both parameters are optional — sensible defaults are inferred:

| Parameter | Default |
|---|---|
| `resource_type` | Schema class name, minus `Schema`/`Create`/`Update` suffix, dasherized, pluralized. `IntakeConfigSchema` → `"intake-configs"` |
| `id_field` | `"id"`, or `"uuid"` if the schema has a `uuid` field but no `id` field |

!!! note
    `jsonapi_meta` must be annotated as `ClassVar[JsonApiMeta]` so that Pydantic does not treat it as a model field.

### Create / Update schemas

Create and update schemas inherit the resource type from the endpoint's `response=` schema, so they often don't need their own `JsonApiMeta`:

```python
class ArticleCreateSchema(BaseModel):
    title: str
    body: str
    # No jsonapi_meta needed — inferred from response schema

class ArticleUpdateSchema(BaseModel):
    title: str | None = None
    body: str | None = None
```

If a body schema is used on an endpoint with no `response=` schema, or you need to override the resource type, add an explicit `JsonApiMeta`:

```python
class ArticleCreateSchema(BaseModel):
    title: str
    body: str
    jsonapi_meta: ClassVar[JsonApiMeta] = JsonApiMeta(resource_type="articles")
```

## Auto-detected relationships

Any schema field whose type is another `BaseModel` with a `JsonApiMeta` is automatically treated as a JSON:API relationship:

```python
class UserSchema(BaseModel):
    id: int
    name: str
    jsonapi_meta: ClassVar[JsonApiMeta] = JsonApiMeta(resource_type="people")

class TagSchema(BaseModel):
    id: int
    name: str
    jsonapi_meta: ClassVar[JsonApiMeta] = JsonApiMeta(resource_type="tags")

class ArticleSchema(BaseModel):
    id: int
    title: str
    author: UserSchema | None = None      # → to-one relationship
    tags: list[TagSchema] = []             # → to-many relationship
    jsonapi_meta: ClassVar[JsonApiMeta] = JsonApiMeta(resource_type="articles")
```

These are rendered as JSON:API `relationships` in the response document. No manual relationship configuration needed.

## CRUD endpoints

### List

```python
@api.get("/articles", response=list[ArticleSchema])
def list_articles(request):
    return Article.objects.all()
```

### Detail

```python
@api.get("/articles/{id}", response=ArticleSchema)
def get_article(request, id: int):
    return Article.objects.get(pk=id)
```

### Create

```python
@api.post("/articles", response={201: ArticleSchema})
def create_article(request, body: ArticleCreateSchema):
    # body is a plain ArticleCreateSchema — not a JSON:API wrapper
    article = Article.objects.create(**body.model_dump())
    return 201, article
```

### Update

```python
from django_ninja_jsonapi import apply_attributes

@api.patch("/articles/{id}", response=ArticleSchema)
def update_article(request, id: int, body: ArticleUpdateSchema):
    article = Article.objects.get(pk=id)
    apply_attributes(article, body, extra_update_fields=["updated_dt"])
    return article
```

### Delete

```python
@api.delete("/articles/{id}", response={204: None})
def delete_article(request, id: int):
    Article.objects.get(pk=id).delete()
    return 204, None
```

## Relationship data in request bodies

When creating or updating resources with relationships, the client sends relationship data in the JSON:API body:

```json
{
  "data": {
    "type": "articles",
    "attributes": { "title": "Hello" },
    "relationships": {
      "author": { "data": { "type": "people", "id": "42" } }
    }
  }
}
```

Access the relationship IDs with `get_rel_id()` and `get_rel_ids()`:

```python
from django_ninja_jsonapi import get_rel_id, get_rel_ids

@api.post("/articles", response={201: ArticleSchema})
def create_article(request, body: ArticleCreateSchema):
    author_id = get_rel_id(request, "author")       # str | None
    tag_ids = get_rel_ids(request, "tags")           # list[str]
    article = Article.objects.create(
        title=body.title,
        author_id=author_id,
    )
    article.tags.set(tag_ids)
    return 201, article
```

Relationship data is stashed on the request during body unwrapping — it's always available but never in the way.

!!! note
    Relationships accepted in the body are inherited from the `response=` schema's relationship fields. If `ArticleSchema` has an `author` relationship, the create endpoint for articles will accept `relationships.author` in the body even if `ArticleCreateSchema` doesn't have an `author` field.

## Pagination, filtering, sorting

These helpers work unchanged — they're already clean:

```python
from django_ninja_jsonapi import jsonapi_paginate, jsonapi_filter, jsonapi_sort

@api.get("/articles", response=list[ArticleSchema])
def list_articles(request):
    qs = Article.objects.all()
    qs = jsonapi_filter(request, qs, allowed_fields={"status", "author"})
    qs = jsonapi_sort(request, qs, allowed_fields={"created_dt", "title"})
    return jsonapi_paginate(request, qs)
```

## Include / sideloading

```python
from django_ninja_jsonapi import parse_include, jsonapi_include

@api.get("/articles", response=list[ArticleSchema])
def list_articles(request):
    includes = parse_include(request)
    qs = Article.objects.all()
    if "author" in includes:
        qs = qs.select_related("author")
    qs = jsonapi_paginate(request, qs)
    # Include related resources
    for article in qs:
        if "author" in includes and article.author:
            jsonapi_include(
                request, article.author,
                resource_type="people",
            )
    return qs
```

## Non-JSON:API endpoints

Schemas **without** `jsonapi_meta` are passed through unchanged (no JSON:API wrapping), so you can have both JSON:API and plain JSON endpoints on the same API.

## Full example

```python
from typing import ClassVar
from pydantic import BaseModel, ConfigDict
from django_ninja_jsonapi import (
    JsonApiMeta,
    NinjaJsonAPI,
    apply_attributes,
    get_rel_id,
    jsonapi_filter,
    jsonapi_paginate,
)
from django_ninja_jsonapi.exceptions import BadRequest, Forbidden


class OrganizationSchema(BaseModel):
    id: int
    name: str
    jsonapi_meta: ClassVar[JsonApiMeta] = JsonApiMeta(resource_type="organizations")


class IntakeConfigSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    uuid: str
    name: str
    organization: OrganizationSchema | None = None
    jsonapi_meta: ClassVar[JsonApiMeta] = JsonApiMeta(
        resource_type="intake-configs", id_field="uuid",
    )


class IntakeConfigCreateSchema(BaseModel):
    name: str
    organization_id: int | None = None


class IntakeConfigUpdateSchema(BaseModel):
    name: str | None = None


api = NinjaJsonAPI(urls_namespace="intake-jsonapi")


@api.get("/intake-configs/", response=list[IntakeConfigSchema])
def list_intake_configs(request):
    qs = IntakeConfig.objects.select_related("organization").all()
    return jsonapi_paginate(request, qs)


@api.get("/intake-configs/{uuid}/", response=IntakeConfigSchema)
def get_intake_config(request, uuid: str):
    return IntakeConfig.objects.select_related("organization").get(uuid=uuid)


@api.post("/intake-configs/", response={201: IntakeConfigSchema})
def create_intake_config(request, body: IntakeConfigCreateSchema):
    config = IntakeConfig.objects.create(**body.model_dump(exclude_unset=True))
    return 201, IntakeConfig.objects.select_related("organization").get(pk=config.pk)


@api.patch("/intake-configs/{uuid}/", response=IntakeConfigSchema)
def update_intake_config(request, uuid: str, body: IntakeConfigUpdateSchema):
    config = IntakeConfig.objects.get(uuid=uuid)
    apply_attributes(config, body, extra_update_fields=["updated_dt"])
    return IntakeConfig.objects.select_related("organization").get(pk=config.pk)


@api.delete("/intake-configs/{uuid}/", response={204: None})
def delete_intake_config(request, uuid: str):
    IntakeConfig.objects.get(uuid=uuid).delete()
    return 204, None
```
