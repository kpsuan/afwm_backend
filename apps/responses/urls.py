"""
AWFM Responses App - URL Configuration
"""

from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import ResponseViewSet, QuestionnaireProgressViewSet, RecordingViewSet

app_name = 'responses'

router = SimpleRouter()
router.register(r'responses', ResponseViewSet, basename='response')
router.register(r'progress', QuestionnaireProgressViewSet, basename='progress')
router.register(r'recordings', RecordingViewSet, basename='recording')

urlpatterns = [
    path('', include(router.urls)),
]
