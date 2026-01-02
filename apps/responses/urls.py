"""
AWFM Responses App - URL Configuration
"""

from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import ResponseViewSet, QuestionnaireProgressViewSet

app_name = 'responses'

router = SimpleRouter()
router.register(r'responses', ResponseViewSet, basename='response')
router.register(r'progress', QuestionnaireProgressViewSet, basename='progress')

urlpatterns = [
    path('', include(router.urls)),
]
