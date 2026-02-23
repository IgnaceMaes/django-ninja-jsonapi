# Standalone renderer

You can use `django-ninja-jsonapi` without `ApplicationBuilder`.

This mode is useful when you want to define Django Ninja endpoints manually and still return JSON:API responses with content type `application/vnd.api+json`.

## Minimal setup

```python
from ninja import NinjaAPI
from pydantic import BaseModel

from django_ninja_jsonapi import JSONAPIRenderer, jsonapi_resource


class ArticleSchema(BaseModel):
    id: int
    title: str


api = NinjaAPI(renderer=JSONAPIRenderer())


@api.get("/articles/{article_id}", response=ArticleSchema)
@jsonapi_resource("articles")
def get_article(request, article_id: int):
    return {"id": article_id, "title": "Hello"}
```

Response shape:

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
  },
  "jsonapi": {
    "version": "1.0"
  }
}
```

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

## Notes

- If your endpoint already returns a JSON:API document (`data`, `errors`, or `jsonapi`), the renderer leaves it unchanged.
- This standalone mode focuses on endpoint-level control and explicit metadata.
- For full auto-generated CRUD/resources/routes and deeper include/query integrations, use `ApplicationBuilder`.
