from typing import Optional

# noinspection PyProtectedMember
from pydantic.fields import FieldInfo

from django_ninja_jsonapi.types_metadata import ClientCanSetId, CustomFilterSQL, CustomSortSQL, RelationshipInfo
from django_ninja_jsonapi.utils.metadata_instance_search import MetadataInstanceSearch

search_client_can_set_id = MetadataInstanceSearch[ClientCanSetId](ClientCanSetId)
search_relationship_info = MetadataInstanceSearch[RelationshipInfo](RelationshipInfo)
search_custom_filter_sql = MetadataInstanceSearch[CustomFilterSQL](CustomFilterSQL)
search_custom_sort_sql = MetadataInstanceSearch[CustomSortSQL](CustomSortSQL)


def get_relationship_info_from_field_metadata(
    field: FieldInfo,
) -> Optional[RelationshipInfo]:
    return search_relationship_info.first(field)
