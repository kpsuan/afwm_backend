"""
ASGI config for AWFM Backend project.

Supports both HTTP and WebSocket protocols via Django Channels.

For more information on this file, see
https://channels.readthedocs.io/en/stable/deploying.html
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

# Initialize Django ASGI application early to ensure AppRegistry is populated
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

# Import WebSocket URL patterns
from apps.communication.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    # HTTP requests handled by Django
    'http': django_asgi_app,

    # WebSocket requests with authentication
    'websocket': AuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})
