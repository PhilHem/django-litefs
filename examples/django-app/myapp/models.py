"""Models for the example app demonstrating LiteFS write/read operations."""

from django.db import models


class Message(models.Model):
    """Simple message model to demonstrate read/write operations."""

    content = models.TextField(
        help_text="Message content",
    )
    node_name = models.CharField(
        max_length=255,
        help_text="Node that created this message",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the message was created",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When the message was last updated",
    )

    class Meta:
        db_table = "myapp_message"
        ordering = ["-created_at"]
        verbose_name = "Message"
        verbose_name_plural = "Messages"

    def __str__(self) -> str:
        return f"Message from {self.node_name}: {self.content[:50]}"
