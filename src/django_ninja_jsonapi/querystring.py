"""Helper to deal with querystring parameters according to jsonapi specification."""

import re
from collections import defaultdict
from functools import cached_property
from typing import Any, Optional
from urllib.parse import unquote

import orjson as json
from django.conf import settings
from django.http import HttpRequest
from pydantic import BaseModel, Field, ValidationError

from django_ninja_jsonapi.exceptions import (
    BadRequest,
    InvalidField,
    InvalidFilters,
    InvalidInclude,
    InvalidType,
)
from django_ninja_jsonapi.storages import schemas_storage


class PaginationQueryStringManager(BaseModel):
    """
    Pagination query string manager.

    Contains info about offsets, sizes, number and limits of query with pagination.
    """

    offset: Optional[int] = None
    size: Optional[int] = 20
    number: int = 1
    limit: Optional[int] = None
    cursor: Optional[str] = None
    next_cursor: Optional[str] = None


class HeadersQueryStringManager(BaseModel):
    """
    Header query string manager.

    Contains info about request headers.
    """

    host: Optional[str] = None
    connection: Optional[str] = None
    accept: Optional[str] = None
    user_agent: Optional[str] = Field(default=None, alias="user-agent")
    referer: Optional[str] = None
    accept_encoding: Optional[str] = Field(default=None, alias="accept-encoding")
    accept_language: Optional[str] = Field(default=None, alias="accept-language")


class QueryStringManager:
    """Querystring parser according to jsonapi reference."""

    managed_keys = ("filter", "page", "fields", "sort", "include")
    jsonapi_query_regex = re.compile(r"^(sort|include)$|^(?P<type>filter|fields|page)(\[[\w\.\-]+\])?$")

    def __init__(self, request: HttpRequest) -> None:
        """
        Initialize instance.

        :param request
        """
        self.request: HttpRequest = request
        self.qs = request.GET
        self.config: dict[str, Any] = getattr(settings, "NINJA_JSONAPI", {})
        self.ALLOW_DISABLE_PAGINATION: bool = self.config.get("ALLOW_DISABLE_PAGINATION", False)
        self.MAX_PAGE_SIZE: int = self.config.get("MAX_PAGE_SIZE", 20)
        self.MAX_INCLUDE_DEPTH: int = self.config.get("MAX_INCLUDE_DEPTH", 3)
        self.headers: HeadersQueryStringManager = HeadersQueryStringManager(**dict(self.request.headers))
        self._validate_query_params()

    def _validate_query_params(self):
        for key in self.qs.keys():
            match = self.jsonapi_query_regex.match(key)
            if not match:
                raise BadRequest(
                    detail=f"Invalid query parameter: {key}",
                    parameter=key,
                )

            if match.group("type") != "filter" and len(self.qs.getlist(key)) > 1:
                raise BadRequest(
                    detail=f"Repeated query parameter not allowed: {key}",
                    parameter=key,
                )

    @classmethod
    def extract_item_key(cls, key: str) -> str:
        try:
            key_start = key.index("[") + 1
            key_end = key.index("]")
            return key[key_start:key_end]
        except Exception as ex:
            msg = "Parse error"
            raise BadRequest(msg, parameter=key) from ex

    def _get_unique_key_values(self, name: str) -> dict[str, str]:
        """
        Return a dict containing key / values items for a given key, used for items like filters, page, etc.

        :param name: name of the querystring parameter
        :return: a dict of key / values items
        :raises BadRequest: if an error occurred while parsing the querystring.
        """
        results = {}

        for raw_key, value in self.qs.lists():
            key = unquote(raw_key)
            if not key.startswith(name):
                continue

            item_key = self.extract_item_key(key)
            if not value:
                continue

            results[item_key] = value[-1]

        return results

    def _get_multiple_key_values(self, name: str) -> dict[str, list]:
        results = defaultdict(list)

        for raw_key, values in self.qs.lists():
            key = unquote(raw_key)
            if not key.startswith(name):
                continue

            item_key = self.extract_item_key(key)
            for value in values:
                results[item_key].extend(value.split(","))

        return results

    @classmethod
    def _simple_filters(cls, dict_: dict[str, Any]) -> list[dict[str, Any]]:
        """Filter creation."""
        return [{"name": key, "op": "eq", "val": value} for (key, value) in dict_.items()]

    @property
    def querystring(self) -> dict[str, str]:
        """
        Return original querystring but containing only managed keys.

        :return: dict of managed querystring parameter
        """
        return {key: value for key, values in self.qs.lists() for value in values if key.startswith(self.managed_keys)}

    @property
    def filters(self) -> list[dict]:
        """
        Return filters from query string.

        :return: filter information
        :raises InvalidFilters: if filter loading from json has failed.
        """
        results = []
        filters = self.qs.get("filter")
        if filters is not None:
            try:
                loaded_filters = json.loads(filters)
            except (ValueError, TypeError) as ex:
                msg = "Parse error"
                raise InvalidFilters(msg) from ex

            if not isinstance(loaded_filters, list):
                msg = f"Incorrect filters format, expected list of conditions but got {type(loaded_filters).__name__}"
                raise InvalidFilters(msg)

            results.extend(loaded_filters)

        if filter_key_values := self._get_unique_key_values("filter["):
            results.extend(self._simple_filters(filter_key_values))

        return results

    @property
    def sorts(self) -> list[dict]:
        if (sort_q := self.qs.get("sort")) is None:
            return []

        sorting_results = []
        for sort_field in sort_q.split(","):
            field, order = sort_field, "asc"

            if sort_field.startswith("-"):
                field = sort_field.removeprefix("-")
                order = "desc"

            relationship_path = None
            if "." in field:
                relationship_path = ".".join(field.split(".")[:-1])

            sorting_results.append({"field": field, "order": order, "rel_path": relationship_path})

        return sorting_results

    @cached_property
    def pagination(self) -> PaginationQueryStringManager:
        """
        Return all page parameters as a dict.

        :return: a dict of pagination information.

        To allow multiples strategies, all parameters starting with `page` will be included. e.g::

            {
                "number": '1',
                "size": '20',
            }

        Example with number strategy:

            query_string = {'page[number]': '2', 'page[size]': '20'}
            parsed_query.pagination
            {'number': '2', 'size': '20'}

        :raises BadRequest: if the client is not allowed to disable pagination.
        """
        # check values type
        pagination_data: dict[str, str] = self._get_unique_key_values("page")
        try:
            pagination = PaginationQueryStringManager(**pagination_data)  # ty: ignore[invalid-argument-type]
        except ValidationError as ex:
            raise BadRequest(detail="Invalid pagination query parameter", parameter="page") from ex

        has_offset_limit_strategy = pagination_data.get("size") is None and (
            pagination_data.get("offset") is not None or pagination_data.get("limit") is not None
        )
        if has_offset_limit_strategy:
            pagination.size = None
            pagination.offset = max(0, pagination.offset or 0)
            if pagination.limit is None or pagination.limit <= 0:
                pagination.limit = 20
            if self.MAX_PAGE_SIZE and pagination.limit > self.MAX_PAGE_SIZE:
                pagination.limit = self.MAX_PAGE_SIZE
            return pagination

        if pagination.size is not None and pagination.size <= 0:
            if pagination.size == 0 and self.ALLOW_DISABLE_PAGINATION:
                pagination.size = None
            else:
                pagination.size = 20

        if pagination.size is not None and self.MAX_PAGE_SIZE and pagination.size > self.MAX_PAGE_SIZE:
            pagination.size = self.MAX_PAGE_SIZE

        return pagination

    @property
    def fields(self) -> dict[str, set]:
        """
        Return fields wanted by client.

        :return: a dict of sparse fieldsets information

        Return value will be a dict containing all fields by resource, for example::

            {
                "user": ['name', 'email'],
            }

        :raises InvalidField: if result field not in schema.
        """
        fields = self._get_multiple_key_values("fields")
        for resource_type, field_names in fields.items():
            if not schemas_storage.has_resource(resource_type):
                msg = f"Application has no resource with type {resource_type!r}"
                raise InvalidType(msg)

            schema = schemas_storage.get_attrs_schema(resource_type, "get")
            assert schema is not None

            for field_name in field_names:
                if field_name == "":
                    continue

                if field_name not in schema.model_fields:
                    msg = f"{schema.__name__} has no attribute {field_name}"
                    raise InvalidField(msg)

        return {resource_type: set(field_names) for resource_type, field_names in fields.items()}

    @property
    def include(self) -> list[str]:
        """
        Return fields to include.

        :return: a list of include information.
        :raises InvalidInclude: if nesting is more than MAX_INCLUDE_DEPTH.
        """
        include_param: str = self.qs.get("include")
        includes = include_param.split(",") if include_param and isinstance(include_param, str) else []

        if self.MAX_INCLUDE_DEPTH is not None:
            for include_path in includes:
                if len(include_path.split(".")) > self.MAX_INCLUDE_DEPTH:
                    msg = f"You can't use include through more than {self.MAX_INCLUDE_DEPTH} relationships"
                    raise InvalidInclude(msg)
        return includes
