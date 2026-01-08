"""
AWFM Communication App - URL Configuration

Notification endpoints.
"""

from django.urls import path
from .views import (
    NotificationListView,
    NotificationDetailView,
    MarkNotificationReadView,
    MarkAllNotificationsReadView,
    UnreadCountView,
)

urlpatterns = [
    # Notifications
    path('notifications/', NotificationListView.as_view(), name='notification-list'),
    path('notifications/mark-all-read/', MarkAllNotificationsReadView.as_view(), name='mark-all-notifications-read'),
    path('notifications/unread-count/', UnreadCountView.as_view(), name='unread-count'),
    path('notifications/<uuid:id>/', NotificationDetailView.as_view(), name='notification-detail'),
    path('notifications/<uuid:id>/read/', MarkNotificationReadView.as_view(), name='mark-notification-read'),
]
