from django.db.models import QuerySet

from django_ninja_jsonapi.data_layers.django_orm.orm import DjangoORMDataLayer


class TenantAwareDataLayer(DjangoORMDataLayer):
    async def get_base_queryset(self) -> QuerySet:
        tenant_id = self.kwargs["tenant_id"]
        return self.model.objects.filter(tenant_id=tenant_id)
