from django_ninja_jsonapi.data_layers.django_orm.orm import DjangoORMDataLayer
from django_ninja_jsonapi.views.view_base import ViewBase


class ViewBaseGeneric(ViewBase):
    data_layer_cls = DjangoORMDataLayer
