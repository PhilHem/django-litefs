"""Django admin configuration for the example app."""

from django.contrib import admin

from myapp.models import Message


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """Admin interface for Message model."""

    list_display = ("content", "node_name", "created_at")
    list_filter = ("node_name", "created_at")
    search_fields = ("content", "node_name")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)
