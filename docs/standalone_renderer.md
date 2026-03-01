# Standalone renderer

You can use `django-ninja-jsonapi` without `ApplicationBuilder`.

This mode is useful when you want to define Django Ninja endpoints manually and still return JSON:API responses with content type `application/vnd.api+json`.

## Quick setup

Use `setup_jsonapi()` to configure your API in one line. It sets the renderer **and** registers the JSON:API exception handler:

```python
from ninja import NinjaAPI
from django_ninja_jsonapi import setup_jsonapi

api = NinjaAPI()
setup_jsonapi(api)
```

This replaces the manual steps of setting `api.renderer = JSONAPIRenderer()` and registering the exception handler separately.

## Minimal example

```python
from ninja import NinjaAPI
from pydantic import BaseModel

from django_ninja_jsonapi import jsonapi_resource, setup_jsonapi


class ArticleSchema(BaseModel):
    id: int
    title: str


api = NinjaAPI()
setup_jsonapi(api)


@api.get("/articles/{article_id}", response=ArticleSchema)
@jsonapi_resource("articles")
def get_article(request, article_id: int):
    return {"id": article_id, "title": "Hello"}
```

Response shape (with `INCLUDE_JSONAPI_OBJECT=True`):

```json
{
  "data": {
    "id": "1",
    "type": "articles",
    "attributes": {
      "title": "Hello"
    },
    "links": {
      "self": "http://testserver/articles/1/"
    }
  },
  "links": {
    "self": "http://testserver/articles/1/"
  }
}
```

When `INCLUDE_JSONAPI_OBJECT` is `True` (or `include_jsonapi_object=True` on the decorator), a `"jsonapi": {"version": "1.0"}` key is also included.

## Returning Pydantic models

Endpoints can return Pydantic model instances directly — the renderer auto-serializes them:

```python
@api.get("/articles/{article_id}")
@jsonapi_resource("articles")
def get_article(request, article_id: int):
    return ArticleSchema(id=article_id, title="Hello")
```

Django model instances are also supported. The renderer converts them to dicts
automatically. Foreign-key fields are serialized as `{"id": <pk>}` so they
work with `relationships=` configuration out of the box. Many-to-many and
reverse relations are **not** included — for those, return a dict or Pydantic
model instead.

## Relationships

Define relationship metadata in `@jsonapi_resource`:

```python
@api.get("/articles/{article_id}")
@jsonapi_resource(
    "articles",
    relationships={
        "author": {"resource_type": "people", "many": False},
        "comments": {"resource_type": "comments", "many": True},
    },
)
def get_article(request, article_id: int):
    return {
        "id": article_id,
        "title": "Hello",
        "author": {"id": 10},
        "comments": [{"id": 100}, {"id": 101}],
    }
```

Relationship fields are emitted under `data.relationships`, and relationship links are generated automatically.

**Tip:** When multiple endpoints share the same resource type, extract relationships into a constant:

```python
ARTICLE_RELATIONSHIPS = {
    "author": {"resource_type": "people", "many": False},
    "comments": {"resource_type": "comments", "many": True},
}


@api.get("/articles/{article_id}", response=jsonapi_response(ArticleSchema, "articles", relationships=ARTICLE_RELATIONSHIPS))
@jsonapi_resource("articles", relationships=ARTICLE_RELATIONSHIPS)
def get_article(request, article_id: int):
    ...
```

## Included, meta, links

Use helper functions to add top-level JSON:API fields:

```python
from django_ninja_jsonapi import jsonapi_include, jsonapi_links, jsonapi_meta


@api.get("/articles/{article_id}")
@jsonapi_resource("articles", relationships={"author": {"resource_type": "people"}})
def get_article(request, article_id: int):
    jsonapi_include(request, {"id": 10, "name": "Alice"}, resource_type="people")
    jsonapi_meta(request, count=1)
    jsonapi_links(request, related="http://example.com/articles/1/author/")
    return {"id": article_id, "title": "Hello", "author": {"id": 10}}
```

## Pagination

### Automatic pagination (recommended)

Use `jsonapi_paginate()` — pass a queryset and it handles everything:

```python
from django_ninja_jsonapi import jsonapi_paginate, jsonapi_resource


@api.get("/articles")
@jsonapi_resource("articles")
def list_articles(request):
    return jsonapi_paginate(request, Article.objects.order_by("id"))
```

This reads `page[number]` and `page[size]` from query parameters, counts the
queryset, slices it, and sets the JSON:API `meta` (`count`, `totalPages`) and
`links` (`first`, `last`, `prev`, `next`) automatically.  Inspired by DRF
JSON:API's built-in pagination behavior.

Options:

| Parameter | Default | Description |
|---|---|---|
| `page_size` | `NINJA_JSONAPI["DEFAULT_PAGE_SIZE"]` or `20` | Default items per page when the client doesn't send `page[size]` |
| `max_page_size` | `NINJA_JSONAPI["MAX_PAGE_SIZE"]` or `100` | Upper bound for client-requested `page[size]` |

Works with Django `QuerySet`, plain `list`, or any sliceable sequence.  Django
model instances in the returned list are auto-serialized by the renderer.

### Low-level pagination

If you need more control, use `jsonapi_pagination()` to set the meta and links
yourself:

```python
from django_ninja_jsonapi import jsonapi_pagination, jsonapi_resource


@api.get("/articles")
@jsonapi_resource("articles")
def list_articles(request):
    qs = Article.objects.all()
    count = qs.count()
    page_number = int(request.GET.get("page[number]", 1))
    page_size = int(request.GET.get("page[size]", 20))
    start = (page_number - 1) * page_size
    items = list(qs[start : start + page_size].values())

    jsonapi_pagination(request, count=count, page_size=page_size, page_number=page_number)
    return items
```

### Cursor-based pagination

For cursor-based strategies, use `jsonapi_cursor_pagination()`:

```python
from django_ninja_jsonapi import jsonapi_cursor_pagination, jsonapi_resource


@api.get("/articles")
@jsonapi_resource("articles")
def list_articles(request):
    cursor = request.GET.get("page[cursor]")
    items, next_cursor, prev_cursor = my_cursor_paginate(cursor, page_size=20)

    jsonapi_cursor_pagination(request, next_cursor=next_cursor, prev_cursor=prev_cursor)
    return items
```

## OpenAPI schema generation

By default, the OpenAPI docs show your flat Pydantic schema rather than the JSON:API envelope. Use `jsonapi_response()` to generate a proper JSON:API response schema:

```python
from django_ninja_jsonapi import jsonapi_resource, jsonapi_response


@api.get("/articles/{article_id}", response=jsonapi_response(ArticleSchema, "articles"))
@jsonapi_resource("articles")
def get_article(request, article_id: int):
    return {"id": article_id, "title": "Hello"}


@api.get("/articles", response=jsonapi_response(ArticleSchema, "articles", many=True))
@jsonapi_resource("articles")
def list_articles(request):
    return [{"id": 1, "title": "Hello"}, {"id": 2, "title": "World"}]
```

The generated schema includes `data.id`, `data.type`, `data.attributes`, `data.relationships`, `links`, `jsonapi`, `meta`, and `included` — matching the actual JSON:API response structure in Swagger UI.

You can also pass `relationships` to include relationship schemas:

```python
@api.get(
    "/articles/{article_id}",
    response=jsonapi_response(
        ArticleSchema,
        "articles",
        relationships={"author": {"resource_type": "people"}},
    ),
)
```

## Parsing JSON:API request bodies

Use `jsonapi_body()` to generate an input schema that parses incoming JSON:API documents:

```python
from django_ninja_jsonapi import jsonapi_body, jsonapi_resource, jsonapi_response


class ArticleCreateSchema(BaseModel):
    title: str
    body: str


@api.post("/articles", response=jsonapi_response(ArticleSchema, "articles"))
@jsonapi_resource("articles")
def create_article(request, payload: jsonapi_body(ArticleCreateSchema, "articles")):
    attrs = payload.data.attributes.model_dump()
    # attrs == {"title": "...", "body": "..."}
    article = Article.objects.create(**attrs)
    return {"id": article.id, "title": article.title, "body": article.body}
```

The generated model expects the standard JSON:API input structure:

```json
{
  "data": {
    "type": "articles",
    "attributes": {
      "title": "My Article",
      "body": "Content here"
    }
  }
}
```

### Client-generated IDs

Pass `allow_id=True` to accept an optional `id` in the request body:

```python
jsonapi_body(ArticleCreateSchema, "articles", allow_id=True)
```

### Relationships in request bodies

```python
jsonapi_body(
    ArticleCreateSchema,
    "articles",
    relationships={"author": {"resource_type": "people"}},
)
```

This accepts:

```json
{
  "data": {
    "type": "articles",
    "attributes": {"title": "Hello", "body": "World"},
    "relationships": {
      "author": {
        "data": {"id": "9", "type": "people"}
      }
    }
  }
}
```

## Error handling

When using `setup_jsonapi()`, JSON:API error responses are handled automatically. You can raise `HTTPException` subclasses anywhere:

```python
from django_ninja_jsonapi import BadRequest, HTTPException
from django_ninja_jsonapi.exceptions import NotFound

# Raises a 400 Bad Request with JSON:API error format
raise BadRequest(detail="Invalid input", pointer="title")

# Raises a 404 Not Found
raise NotFound(detail="Article not found")
```

If not using `setup_jsonapi()`, register the handler manually:

```python
from django_ninja_jsonapi.exceptions import HTTPException
from django_ninja_jsonapi.exceptions.handlers import base_exception_handler

api.add_exception_handler(HTTPException, base_exception_handler)
```

## Full CRUD example

```python
from ninja import NinjaAPI
from pydantic import BaseModel

from django_ninja_jsonapi import (
    jsonapi_body,
    jsonapi_paginate,
    jsonapi_resource,
    jsonapi_response,
    setup_jsonapi,
)


class ArticleSchema(BaseModel):
    id: int
    title: str
    body: str


class ArticleCreateSchema(BaseModel):
    title: str
    body: str


api = NinjaAPI()
setup_jsonapi(api)


@api.get("/articles", response=jsonapi_response(ArticleSchema, "articles", many=True))
@jsonapi_resource("articles")
def list_articles(request):
    return jsonapi_paginate(request, Article.objects.order_by("id"))


@api.get("/articles/{article_id}", response=jsonapi_response(ArticleSchema, "articles"))
@jsonapi_resource("articles")
def get_article(request, article_id: int):
    article = Article.objects.get(id=article_id)
    return {"id": article.id, "title": article.title, "body": article.body}


@api.post("/articles", response=jsonapi_response(ArticleSchema, "articles"))
@jsonapi_resource("articles")
def create_article(request, payload: jsonapi_body(ArticleCreateSchema, "articles")):
    attrs = payload.data.attributes.model_dump()
    article = Article.objects.create(**attrs)
    return {"id": article.id, "title": article.title, "body": article.body}


@api.patch("/articles/{article_id}", response=jsonapi_response(ArticleSchema, "articles"))
@jsonapi_resource("articles")
def update_article(request, article_id: int, payload: jsonapi_body(ArticleCreateSchema, "articles")):
    article = Article.objects.get(id=article_id)
    for key, value in payload.data.attributes.model_dump(exclude_unset=True).items():
        setattr(article, key, value)
    article.save()
    return {"id": article.id, "title": article.title, "body": article.body}


@api.delete("/articles/{article_id}")
def delete_article(request, article_id: int):
    Article.objects.filter(id=article_id).delete()
    return {"success": True}
```

## Notes

- If your endpoint already returns a JSON:API document (`data`, `errors`, or `jsonapi`), the renderer leaves it unchanged.
- This standalone mode focuses on endpoint-level control and explicit metadata.
- For full auto-generated CRUD/resources/routes and deeper include/query integrations, use `ApplicationBuilder`.
