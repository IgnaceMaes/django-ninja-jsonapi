# Custom filtering

This project is Django ORM-only, but you can still customize filtering behavior by extending query translation.

## Approach

1. Parse incoming filter payload using `QueryStringManager`.
2. Translate filter objects into Django ORM expressions in your data-layer extension.
3. Register your custom view/data-layer wiring in `ApplicationBuilder` resource config.

## Example

```python
from django.db.models import Q

from django_ninja_jsonapi.data_layers.django_orm.orm import DjangoORMDataLayer


class CustomFilterDataLayer(DjangoORMDataLayer):
	def _apply_custom_filter(self, queryset, one_filter: dict):
		if one_filter.get("op") == "starts_with_ci":
			field = one_filter["name"].replace(".", "__")
			return queryset.filter(**{f"{field}__istartswith": one_filter["val"]})
		return queryset
```

## Typical customizations

- map custom operators to `Q(...)` expressions
- enforce allow-lists for filterable fields
- inject tenant/permission scoping filters
