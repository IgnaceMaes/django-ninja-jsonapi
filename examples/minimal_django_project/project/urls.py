from django.urls import path
from jsonapi_app.api import api

urlpatterns = [
    path("api/", api.urls),
]
