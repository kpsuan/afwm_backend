"""
WebSocket URL routing for the communication app.

WebSocket endpoints:
- /ws/notifications/ - Real-time notifications for authenticated users
"""

from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/notifications/$', consumers.NotificationConsumer.as_asgi()),
]
