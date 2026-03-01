from unittest.mock import MagicMock

from ninja import NinjaAPI

from django_ninja_jsonapi.renderers import JSONAPIRenderer
from django_ninja_jsonapi.setup import setup_jsonapi


class TestSetupJsonapi:
    def test_sets_renderer(self):
        api = NinjaAPI()
        setup_jsonapi(api)

        assert isinstance(api.renderer, JSONAPIRenderer)

    def test_custom_renderer(self):
        api = NinjaAPI()
        custom_renderer = JSONAPIRenderer()
        setup_jsonapi(api, renderer=custom_renderer)

        assert api.renderer is custom_renderer

    def test_registers_exception_handler(self):
        api = NinjaAPI()
        api.add_exception_handler = MagicMock()
        setup_jsonapi(api)

        api.add_exception_handler.assert_called_once()
        from django_ninja_jsonapi.exceptions import HTTPException
        from django_ninja_jsonapi.exceptions.handlers import base_exception_handler

        call_args = api.add_exception_handler.call_args
        assert call_args[0][0] is HTTPException
        assert call_args[0][1] is base_exception_handler

    def test_custom_exception_handler(self):
        api = NinjaAPI()
        api.add_exception_handler = MagicMock()

        def custom_handler(req, exc):
            return None

        setup_jsonapi(api, exception_handler=custom_handler)

        call_args = api.add_exception_handler.call_args
        assert call_args[0][1] is custom_handler
