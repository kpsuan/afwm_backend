"""
AWFM Content App - URL Configuration

Registers API endpoints for content models.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.content import views

# Create router and register viewsets
router = DefaultRouter()
router.register(r'questions', views.QuestionViewSet, basename='question')
router.register(r'layers', views.LayerViewSet, basename='layer')
router.register(r'options', views.OptionViewSet, basename='option')
router.register(r'components', views.ComponentViewSet, basename='component')
router.register(r'ppr', views.PPRViewSet, basename='ppr')

app_name = 'content'

urlpatterns = [
    path('', include(router.urls)),
    path('upload-image/', views.ImageUploadView.as_view(), name='upload-image'),
]
