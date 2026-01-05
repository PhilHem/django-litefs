"""URL configuration for LiteFS Django adapter health check endpoints.

Usage in Django project's urls.py:
    from django.urls import include, path

    urlpatterns = [
        # ... other patterns
        path("", include("litefs_django.urls")),
    ]

This will expose:
    /health/ - Full health status (leader, health, cluster state)
    /health/live - Liveness probe (is LiteFS running?)
    /health/ready - Readiness probe (can accept traffic?)
"""

from django.urls import path

from litefs_django.views import health_check_view, liveness_view, readiness_view

app_name = "litefs_django"

urlpatterns = [
    path("health/", health_check_view, name="health_check"),
    path("health/live", liveness_view, name="liveness"),
    path("health/ready", readiness_view, name="readiness"),
]
