"""
AWFM Communication App - Serializers

Serializers for notifications.
"""

from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for displaying notification info."""
    is_read = serializers.BooleanField(read_only=True)

    class Meta:
        model = Notification
        fields = (
            'id',
            'notification_type',
            'title',
            'body',
            'metadata',
            'is_read',
            'read_at',
            'created_at',
        )
        read_only_fields = fields


class NotificationListSerializer(serializers.ModelSerializer):
    """Lighter serializer for listing notifications."""
    is_read = serializers.BooleanField(read_only=True)

    class Meta:
        model = Notification
        fields = (
            'id',
            'notification_type',
            'title',
            'body',
            'metadata',
            'is_read',
            'created_at',
        )
        read_only_fields = fields
