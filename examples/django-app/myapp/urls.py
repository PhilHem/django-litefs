"""URL configuration for the example app."""

from django.urls import path

from myapp import views

urlpatterns = [
    path("health/", views.health_check, name="health_check"),
    path("messages/", views.list_messages, name="list_messages"),
    path("messages/create/", views.create_message, name="create_message"),
    path("stats/", views.stats, name="stats"),
]
