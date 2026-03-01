from django.urls import path
from jsonapi_app.api import api
from jsonapi_app.api_standalone import api as standalone_api

urlpatterns = [
    path("api/", api.urls),
    path("api-standalone/", standalone_api.urls),
]
