from typing import Annotated

from pydantic import BaseModel

from django_ninja_jsonapi.utils.metadata_instance_search import MetadataInstanceSearch


class Marker:
    def __init__(self, value: str):
        self.value = value


class ExampleSchema(BaseModel):
    name: Annotated[str, Marker("alpha"), Marker("beta")]


def test_metadata_instance_search_iterate_and_first():
    field = ExampleSchema.model_fields["name"]
    search = MetadataInstanceSearch(Marker)

    markers = list(search.iterate(field))

    assert [marker.value for marker in markers] == ["alpha", "beta"]
    assert search.first(field).value == "alpha"
