import copy

import pytest

from django_ninja_jsonapi.atomic.prepared_atomic_operation import atomic_dependency_handlers
from django_ninja_jsonapi.storages.models_storage import models_storage
from django_ninja_jsonapi.storages.schemas_storage import schemas_storage
from django_ninja_jsonapi.storages.views_storage import views_storage


@pytest.fixture(autouse=True)
def reset_global_storages():
    models_snapshot = (
        copy.copy(models_storage._models),
        copy.copy(models_storage._id_field_names),
        copy.copy(models_storage._resource_paths),
    )
    schemas_snapshot = (
        copy.deepcopy(schemas_storage._data),
        copy.copy(schemas_storage._source_schemas),
        copy.copy(schemas_storage._jsonapi_object_schemas),
    )
    views_snapshot = copy.copy(views_storage._views)
    atomic_snapshot = copy.copy(atomic_dependency_handlers)

    yield

    models_storage._models = models_snapshot[0]
    models_storage._id_field_names = models_snapshot[1]
    models_storage._resource_paths = models_snapshot[2]

    schemas_storage._data = schemas_snapshot[0]
    schemas_storage._source_schemas = schemas_snapshot[1]
    schemas_storage._jsonapi_object_schemas = schemas_snapshot[2]

    views_storage._views = views_snapshot

    atomic_dependency_handlers.clear()
    atomic_dependency_handlers.update(atomic_snapshot)
