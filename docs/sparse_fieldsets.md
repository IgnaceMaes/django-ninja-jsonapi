# Sparse fieldsets

Use the `fields` query parameter to limit returned attributes and relationship sections.

## Syntax

```text
fields[<resource_type>]=field1,field2
```

## Examples

```http
GET /customers?fields[customer]=name
GET /customers/1?include=computers&fields[computer]=serial
GET /customers/1?include=computers&fields[customer]=name,computers&fields[computer]=serial
```

```python
import httpx

response = httpx.get(
	"http://localhost:8000/api/customers/1",
	params={
		"include": "computers",
		"fields[customer]": "name,computers",
		"fields[computer]": "serial",
	},
)
print(response.json())
```

Example effect:

```json
{
	"links": {"self": "http://localhost:8000/api/customers/1?include=computers&fields%5Bcustomer%5D=name,computers&fields%5Bcomputer%5D=serial"},
	"data": {
		"type": "customer",
		"id": "1",
		"attributes": {"name": "John"},
		"links": {"self": "http://localhost:8000/api/customers/1/"}
	},
	"included": [
		{
			"type": "computer",
			"id": "10",
			"attributes": {"serial": "ABC-123"},
			"links": {"self": "http://localhost:8000/api/computers/10/"}
		}
	]
}
```

When combining `include` with `fields`, keep included relationships in the parent resource fieldset.
