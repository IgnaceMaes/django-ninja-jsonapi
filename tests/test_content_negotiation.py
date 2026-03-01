"""Tests for JSON:API content negotiation (415 / 406)."""

import pytest
from django.test import RequestFactory

from django_ninja_jsonapi.content_negotiation import validate_accept, validate_content_type
from django_ninja_jsonapi.exceptions.json_api import NotAcceptable, UnsupportedMediaType

factory = RequestFactory()


class TestValidateContentType:
    """Content-Type header validation."""

    def test_no_content_type_passes(self):
        request = factory.get("/")
        validate_content_type(request)  # should not raise

    def test_exact_jsonapi_content_type_passes(self):
        request = factory.post("/", content_type="application/vnd.api+json")
        validate_content_type(request)

    def test_regular_json_content_type_raises_415(self):
        """Non-JSON:API content type is rejected."""
        request = factory.post("/", content_type="application/json")
        with pytest.raises(UnsupportedMediaType) as exc_info:
            validate_content_type(request)
        assert exc_info.value.status_code == 415

    def test_jsonapi_with_media_type_params_raises_415(self):
        request = factory.post("/", content_type="application/vnd.api+json; charset=utf-8")
        with pytest.raises(UnsupportedMediaType) as exc_info:
            validate_content_type(request)
        assert exc_info.value.status_code == 415

    def test_jsonapi_with_profile_param_raises_415(self):
        request = factory.post("/", content_type="application/vnd.api+json; profile=custom")
        with pytest.raises(UnsupportedMediaType) as exc_info:
            validate_content_type(request)
        assert exc_info.value.status_code == 415


class TestValidateAccept:
    """Accept header validation."""

    def test_no_accept_header_passes(self):
        request = factory.get("/")
        validate_accept(request)

    def test_accept_star_passes(self):
        request = factory.get("/", HTTP_ACCEPT="*/*")
        validate_accept(request)

    def test_accept_bare_jsonapi_passes(self):
        request = factory.get("/", HTTP_ACCEPT="application/vnd.api+json")
        validate_accept(request)

    def test_accept_json_passes(self):
        request = factory.get("/", HTTP_ACCEPT="application/json")
        validate_accept(request)

    def test_accept_jsonapi_with_params_only_raises_406(self):
        request = factory.get("/", HTTP_ACCEPT="application/vnd.api+json; charset=utf-8")
        with pytest.raises(NotAcceptable) as exc_info:
            validate_accept(request)
        assert exc_info.value.status_code == 406

    def test_accept_mixed_jsonapi_bare_and_params_passes(self):
        """At least one bare JSON:API entry exists → accept."""
        request = factory.get(
            "/",
            HTTP_ACCEPT="application/vnd.api+json; charset=utf-8, application/vnd.api+json",
        )
        validate_accept(request)

    def test_accept_all_jsonapi_entries_with_params_raises_406(self):
        request = factory.get(
            "/",
            HTTP_ACCEPT="application/vnd.api+json; ext=bulk, application/vnd.api+json; profile=x",
        )
        with pytest.raises(NotAcceptable) as exc_info:
            validate_accept(request)
        assert exc_info.value.status_code == 406

    def test_accept_jsonapi_with_q_factor_only_passes(self):
        """q= is an accept-extension, not a media type parameter."""
        request = factory.get("/", HTTP_ACCEPT="application/vnd.api+json; q=0.9")
        validate_accept(request)
