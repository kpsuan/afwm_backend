"""
AWFM Communication App - Views

API views for notifications management.
"""

from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification
from .serializers import NotificationSerializer, NotificationListSerializer


class NotificationListView(generics.ListAPIView):
    """
    List notifications for the current user.

    GET /api/v1/notifications/
    Query params:
        - unread_only: Filter to only unread notifications (default: false)
        - limit: Number of notifications to return (default: 50)
    """
    permission_classes = (IsAuthenticated,)
    serializer_class = NotificationListSerializer

    def get_queryset(self):
        queryset = Notification.objects.filter(user=self.request.user)

        # Filter by unread if requested
        unread_only = self.request.query_params.get('unread_only', 'false').lower() == 'true'
        if unread_only:
            queryset = queryset.filter(read_at__isnull=True)

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        # Apply limit
        limit = int(request.query_params.get('limit', 50))
        queryset = queryset[:limit]

        serializer = self.get_serializer(queryset, many=True)

        # Get unread count
        unread_count = Notification.objects.filter(
            user=request.user,
            read_at__isnull=True
        ).count()

        return Response({
            'notifications': serializer.data,
            'unread_count': unread_count,
        })


class NotificationDetailView(generics.RetrieveDestroyAPIView):
    """
    Get or delete a specific notification.

    GET /api/v1/notifications/{id}/
    DELETE /api/v1/notifications/{id}/
    """
    permission_classes = (IsAuthenticated,)
    serializer_class = NotificationSerializer
    lookup_field = 'id'

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)


class MarkNotificationReadView(APIView):
    """
    Mark a notification as read.

    POST /api/v1/notifications/{id}/read/
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request, id):
        try:
            notification = Notification.objects.get(id=id, user=request.user)
        except Notification.DoesNotExist:
            return Response({
                'error': 'Notification not found'
            }, status=status.HTTP_404_NOT_FOUND)

        notification.mark_as_read()

        return Response({
            'message': 'Notification marked as read',
            'notification': NotificationSerializer(notification).data
        })


class MarkAllNotificationsReadView(APIView):
    """
    Mark all notifications as read.

    POST /api/v1/notifications/mark-all-read/
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        updated = Notification.objects.filter(
            user=request.user,
            read_at__isnull=True
        ).update(read_at=timezone.now())

        return Response({
            'message': f'{updated} notifications marked as read',
            'unread_count': 0
        })


class UnreadCountView(APIView):
    """
    Get the count of unread notifications.

    GET /api/v1/notifications/unread-count/
    """
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        count = Notification.objects.filter(
            user=request.user,
            read_at__isnull=True
        ).count()

        return Response({
            'unread_count': count
        })
