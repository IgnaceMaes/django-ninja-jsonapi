# Schema-aware model coercion

The renderer's `_coerce_to_dict` method can use a Pydantic schema to serialize Django model instances, including `@property` fields that aren't database columns.

## Problem

By default, the renderer iterates `_meta.get_fields()` which only includes actual database fields. Model properties like `organization_name` or `computed_field` are invisible:

```python
class Article(models.Model):
    title = models.CharField(max_length=200)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)

    @property
    def organization_name(self) -> str:
        return self.organization.name
```

Without a schema, `organization_name` won't appear in the JSON:API response.

## Solution

Pass a `schema` parameter to `@jsonapi_resource()`:

```python
class ArticleSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    organization_name: str


@api.get("/articles/{article_id}")
@jsonapi_resource("articles", schema=ArticleSchema)
def get_article(request, article_id: int):
    return Article.objects.select_related("organization").get(id=article_id)
```

When a schema is provided, the renderer uses `schema.model_validate(instance, from_attributes=True).model_dump()` instead of iterating `_meta.get_fields()`. This gives access to all fields defined in the schema, including properties, via Pydantic's `from_attributes=True`.

## With `JsonApiResource`

The schema is automatically passed through when using `JsonApiResource`:

```python
ArticleResource = JsonApiResource(
    resource_type="articles",
    schema=ArticleSchema,
    relationships={"organization": {"resource_type": "organizations"}},
)

@api.get("/articles/{article_id}", response=ArticleResource.response())
@ArticleResource.decorator()
def get_article(request, article_id: int):
    return Article.objects.select_related("organization").get(id=article_id)
```

## Notes

- The schema must have `model_config = ConfigDict(from_attributes=True)` for property access to work.
- Without a schema, the renderer falls back to the default `_meta.get_fields()` behavior.
- This also works for includes via `jsonapi_include()` when the included resource's config has a schema.
