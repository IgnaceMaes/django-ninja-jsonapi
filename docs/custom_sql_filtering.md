# Custom filtering

This project is Django ORM-only, but you can still customize filtering behavior by extending query translation.

## Approach

1. Parse incoming filter payload using `QueryStringManager`.
2. Translate filter objects into Django ORM expressions in your data-layer extension.
3. Register your custom view/data-layer wiring in `ApplicationBuilder` resource config.

## Typical customizations

- map custom operators to `Q(...)` expressions
- enforce allow-lists for filterable fields
- inject tenant/permission scoping filters
