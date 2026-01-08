"""
URL configuration for AWFM Backend project.

AWFM: A Whole Family Matter
Interdependent Care Planning (ICP) Platform
"""
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    # Django Admin
    path('admin/', admin.site.urls),

    # API Documentation (OpenAPI/Swagger)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # API v1 endpoints
    path('api/v1/auth/', include('apps.accounts.urls')),  # Authentication API enabled
    path('api/v1/teams/', include('apps.teams.urls')),  # Teams API enabled
    path('api/v1/content/', include('apps.content.urls')),  # Content API enabled
    path('api/v1/user/', include('apps.responses.urls')),  # User responses API enabled
    path('api/v1/', include('apps.communication.urls')),  # Notifications API enabled
]
