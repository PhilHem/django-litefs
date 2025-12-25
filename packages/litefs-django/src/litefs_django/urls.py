"""URL configuration for LiteFS Django adapter health check endpoint."""

from django.urls import path

from litefs_django.views import health_check_view

app_name = "litefs_django"

urlpatterns = [
    path("health/", health_check_view, name="health_check"),
]
