"""
JWT Authentication Middleware for WebSockets.

Since WebSockets don't support HTTP headers in the same way,
we pass the JWT token via query string: ws://host/ws/notifications/?token=<jwt>
"""

from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


@database_sync_to_async
def get_user_from_token(token_string):
    """Validate JWT token and return the user."""
    try:
        from apps.accounts.models import User

        # Validate the token
        access_token = AccessToken(token_string)
        user_id = access_token.get('user_id')

        if user_id:
            return User.objects.get(id=user_id)
        return AnonymousUser()

    except (InvalidToken, TokenError, User.DoesNotExist):
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """
    JWT Authentication middleware for Django Channels.

    Extracts JWT token from query string and authenticates the user.

    Usage:
        Connect with: ws://host/ws/notifications/?token=<jwt_access_token>
    """

    async def __call__(self, scope, receive, send):
        # Copy scope to avoid mutation issues
        scope = dict(scope)

        # Extract token from query string
        query_string = scope.get('query_string', b'').decode()
        query_params = parse_qs(query_string)
        token_list = query_params.get('token', [])

        if token_list:
            token = token_list[0]
            user = await get_user_from_token(token)
            scope['user'] = user
        else:
            scope['user'] = AnonymousUser()

        return await self.inner(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    """
    Convenience wrapper that applies JWT auth middleware.

    Usage in asgi.py:
        from apps.communication.middleware import JWTAuthMiddlewareStack

        application = ProtocolTypeRouter({
            'websocket': JWTAuthMiddlewareStack(
                URLRouter(websocket_urlpatterns)
            ),
        })
    """
    return JWTAuthMiddleware(inner)
