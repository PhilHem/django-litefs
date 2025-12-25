"""Views for the example app."""

import os
import json
from datetime import datetime

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import connection

from myapp.models import Message


def get_node_name() -> str:
    """Get the current node name from environment."""
    return os.getenv("NODE_NAME", "unknown")


@require_http_methods(["GET"])
def health_check(request):
    """Health check endpoint returning node and database info."""
    node_name = get_node_name()

    # Get database path to verify LiteFS mount
    db_name = connection.settings_dict.get("NAME", "unknown")

    try:
        # Simple query to verify DB connectivity
        message_count = Message.objects.count()
        status = "healthy"
    except Exception as e:
        message_count = 0
        status = f"error: {str(e)}"

    return JsonResponse({
        "status": status,
        "node_name": node_name,
        "database": db_name,
        "message_count": message_count,
        "timestamp": datetime.utcnow().isoformat(),
    })


@require_http_methods(["GET"])
def list_messages(request):
    """List all messages in the database."""
    node_name = get_node_name()

    try:
        messages = Message.objects.all()
        return JsonResponse({
            "node_name": node_name,
            "message_count": messages.count(),
            "messages": [
                {
                    "id": msg.id,
                    "content": msg.content,
                    "node_name": msg.node_name,
                    "created_at": msg.created_at.isoformat(),
                }
                for msg in messages[:100]  # Limit to 100 for API response
            ],
            "timestamp": datetime.utcnow().isoformat(),
        })
    except Exception as e:
        return JsonResponse(
            {
                "error": str(e),
                "node_name": node_name,
            },
            status=500,
        )


@require_http_methods(["POST"])
def create_message(request):
    """Create a new message (write operation on primary only)."""
    node_name = get_node_name()

    try:
        # Parse JSON body
        body = json.loads(request.body)
        content = body.get("content", "").strip()

        if not content:
            return JsonResponse(
                {
                    "error": "content field is required and must not be empty",
                    "node_name": node_name,
                },
                status=400,
            )

        # Create message - will fail if not primary
        message = Message.objects.create(
            content=content,
            node_name=node_name,
        )

        return JsonResponse(
            {
                "success": True,
                "message_id": message.id,
                "content": message.content,
                "node_name": message.node_name,
                "created_at": message.created_at.isoformat(),
                "timestamp": datetime.utcnow().isoformat(),
            },
            status=201,
        )
    except json.JSONDecodeError:
        return JsonResponse(
            {
                "error": "Invalid JSON in request body",
                "node_name": node_name,
            },
            status=400,
        )
    except Exception as e:
        return JsonResponse(
            {
                "error": str(e),
                "error_type": type(e).__name__,
                "node_name": node_name,
            },
            status=500,
        )


@require_http_methods(["GET"])
def stats(request):
    """Get cluster stats including message count and replication info."""
    node_name = get_node_name()

    try:
        # Count messages and group by node to show replication
        all_messages = Message.objects.all()
        total_count = all_messages.count()

        # Group by node
        node_stats = {}
        for msg in all_messages:
            if msg.node_name not in node_stats:
                node_stats[msg.node_name] = 0
            node_stats[msg.node_name] += 1

        return JsonResponse({
            "node_name": node_name,
            "total_messages": total_count,
            "by_node": node_stats,
            "timestamp": datetime.utcnow().isoformat(),
        })
    except Exception as e:
        return JsonResponse(
            {
                "error": str(e),
                "node_name": node_name,
            },
            status=500,
        )
