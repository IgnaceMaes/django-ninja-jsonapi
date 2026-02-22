from ninja.renderers import JSONRenderer

JSONAPI_MEDIA_TYPE = "application/vnd.api+json"


class JSONAPIRenderer(JSONRenderer):
    media_type = JSONAPI_MEDIA_TYPE
