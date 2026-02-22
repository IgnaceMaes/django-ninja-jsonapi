# Sparse fieldsets

Use the `fields` query parameter to limit returned attributes and relationship sections.

## Syntax

```text
fields[<resource_type>]=field1,field2
```

## Examples

```http
GET /users?fields[user]=name
GET /users/1?include=computers&fields[computer]=serial
GET /users/1?include=computers&fields[user]=name,computers&fields[computer]=serial
```

When combining `include` with `fields`, keep included relationships in the parent resource fieldset.
