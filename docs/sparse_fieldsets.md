# Sparse fieldsets

Use the `fields` query parameter to limit returned attributes and relationship sections.

## Syntax

```text
fields[<resource_type>]=field1,field2
```

## Examples

```http
GET /customers?fields[customers]=name
GET /customers/1?include=computers&fields[computers]=serial
GET /customers/1?include=computers&fields[customers]=name,computers&fields[computers]=serial
```

```python
import httpx

response = httpx.get(
	"http://localhost:8000/api/customers/1",
	params={
		"include": "computers",
		"fields[customers]": "name,computers",
		"fields[computers]": "serial",
	},
)
print(response.json())
```

Example effect:

```json
{
	"links": {"self": "http://localhost:8000/api/customers/1?include=computers&fields%5Bcustomers%5D=name,computers&fields%5Bcomputers%5D=serial"},
	"data": {
		"type": "customers",
		"id": "1",
		"attributes": {"name": "John"},
		"links": {"self": "http://localhost:8000/api/customers/1/"}
	},
	"included": [
		{
			"type": "computers",
			"id": "10",
			"attributes": {"serial": "ABC-123"},
			"links": {"self": "http://localhost:8000/api/computers/10/"}
		}
	]
}
```

When combining `include` with `fields`, keep included relationships in the parent resource fieldset.
