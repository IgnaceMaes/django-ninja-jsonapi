from django_ninja_jsonapi.data_layers.sqla.orm import SqlalchemyDataLayer
from django_ninja_jsonapi.views.view_base import ViewBase


class ViewBaseGeneric(ViewBase):
    data_layer_cls = SqlalchemyDataLayer
