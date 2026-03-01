"""
JSON:API content negotiation utilities.

Implements the JSON:API content negotiation requirements from the spec:
https://jsonapi.org/format/#content-negotiation

- Servers MUST return 415 Unsupported Media Type if a request specifies the
  ``Content-Type: application/vnd.api+json`` header with any media type parameters.
- Servers MUST return 406 Not Acceptable if a request's ``Accept`` header contains
  the JSON:API media type and all instances include media type parameters.
"""

from __future__ import annotations

from django.http import HttpRequest

from django_ninja_jsonapi.exceptions.json_api import NotAcceptable, UnsupportedMediaType
from django_ninja_jsonapi.renderers import JSONAPI_MEDIA_TYPE

_JSONAPI_ESSENCE = JSONAPI_MEDIA_TYPE  # "application/vnd.api+json"


def _parse_media_ranges(header_value: str) -> list[tuple[str, bool]]:
    """
    Parse a Content-Type or Accept header into a list of
    ``(media_type_essence, has_params)`` tuples.

    Parameters attached to a media type (e.g. ``charset=utf-8``) are flagged
    but not preserved — the JSON:API spec only cares whether they exist.
    """
    results: list[tuple[str, bool]] = []
    for part in header_value.split(","):
        part = part.strip()
        if not part:
            continue
        segments = [s.strip() for s in part.split(";")]
        media_type = segments[0].lower()
        # "q" is a standard accept-extension, not a media type parameter
        params = [s for s in segments[1:] if s and not s.startswith("q=")]
        results.append((media_type, bool(params)))
    return results


def validate_content_type(request: HttpRequest) -> None:
    """
    Validate the ``Content-Type`` header of an incoming request.

    Raises :class:`UnsupportedMediaType` when:

    * the header value is ``application/vnd.api+json`` with extra media type
      parameters (e.g. ``application/vnd.api+json; charset=utf-8``), per the
      JSON:API spec, **or**
    * the header does not contain the JSON:API media type at all (e.g.
      ``application/json``), since JSON:API endpoints expect the JSON:API
      content type.

    Only applicable for requests that carry a body (POST, PATCH, DELETE with body).
    """
    raw = request.META.get("CONTENT_TYPE", "")
    if not raw:
        return

    ranges = _parse_media_ranges(raw)

    found_jsonapi = False
    for media_type, has_params in ranges:
        if media_type == _JSONAPI_ESSENCE:
            found_jsonapi = True
            if has_params:
                raise UnsupportedMediaType(
                    detail=(
                        "JSON:API requests MUST NOT include media type parameters "
                        "in the Content-Type header. "
                        f"Received: {raw!r}"
                    ),
                )

    if not found_jsonapi:
        raise UnsupportedMediaType(
            detail=(f"JSON:API endpoints require Content-Type: {_JSONAPI_ESSENCE}. Received: {raw!r}"),
        )


def validate_accept(request: HttpRequest) -> None:
    """
    Validate the ``Accept`` header of an incoming request.

    Raises :class:`NotAcceptable` when all JSON:API media types in the
    ``Accept`` header include media type parameters, making it impossible
    for the server to fulfil the request with a spec-compliant response.

    If the ``Accept`` header does not mention ``application/vnd.api+json``
    at all, or includes at least one bare ``application/vnd.api+json``
    entry, the request is accepted.
    """
    accept = request.META.get("HTTP_ACCEPT", "")
    if not accept:
        return

    ranges = _parse_media_ranges(accept)
    jsonapi_ranges = [(mt, hp) for mt, hp in ranges if mt == _JSONAPI_ESSENCE]

    # If no JSON:API media types mentioned, nothing to enforce
    if not jsonapi_ranges:
        return

    # If every JSON:API entry has parameters, reject
    if all(has_params for _, has_params in jsonapi_ranges):
        raise NotAcceptable(
            detail=(
                "All JSON:API media types in the Accept header include "
                "media type parameters. The server cannot produce a "
                "response that satisfies the request. "
                f"Received Accept: {accept!r}"
            ),
        )
