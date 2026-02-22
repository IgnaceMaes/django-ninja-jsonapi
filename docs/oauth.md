# OAuth

OAuth integration is not bundled as a first-class module in this package.

Use Django authentication providers and Ninja auth hooks, then map authorization failures to JSON:API error responses.

## Example pattern

```python
from ninja import NinjaAPI
from ninja.security import HttpBearer


class OAuthBearer(HttpBearer):
	def authenticate(self, request, token):
		if not token:
			return None
		return {"token": token}


api = NinjaAPI(auth=OAuthBearer())
```

Combine this with `OperationConfig` dependency checks in your views to enforce scope/resource-level authorization.

Future docs may include end-to-end examples with common Django OAuth providers.
