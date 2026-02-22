# Include many-to-many

Many-to-many relationships can be represented with relationship links and optional `include` expansions.

## Example

```http
GET /groups/1?include=users
```

```python
import httpx

response = httpx.get("http://localhost:8000/api/groups/1", params={"include": "users"})
print(response.json())
```

## Relationship link endpoint

```http
GET /groups/1/relationships/users
```

Use relationship-link endpoints for linkage-only payloads, and `include` for full related resource payloads.
