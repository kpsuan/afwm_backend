"""
AWFM Responses App - Views
"""

from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response as DRFResponse
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q, Max
from .models import Response, QuestionnaireProgress
from .serializers import (
    ResponseSerializer,
    QuestionnaireProgressSerializer,
    ResponseSummarySerializer
)
from apps.content.models import Question


class ResponseViewSet(viewsets.ModelViewSet):
    """ViewSet for managing user responses."""

    serializer_class = ResponseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return responses for the authenticated user."""
        return Response.objects.filter(user=self.request.user).select_related(
            'question', 'layer'
        )

    def perform_create(self, serializer):
        """Save the response with the current user."""
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'], url_path='by-question/(?P<question_id>[^/.]+)')
    def by_question(self, request, question_id=None):
        """Get all responses for a specific question."""
        responses = self.get_queryset().filter(question_id=question_id)
        serializer = self.get_serializer(responses, many=True)
        return DRFResponse(serializer.data)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get summary of all user responses grouped by question."""
        user = request.user
        questions = Question.objects.filter(
            responses__user=user
        ).distinct().prefetch_related('responses', 'layers')

        summary_data = []

        for question in questions:
            user_responses = Response.objects.filter(
                user=user,
                question=question
            ).select_related('layer')

            total_layers = question.layers.count()
            completed_layers = user_responses.filter(
                completed_at__isnull=False
            ).count()

            summary_data.append({
                'question_id': question.id,
                'question_title': question.title,
                'total_layers': total_layers,
                'completed_layers': completed_layers,
                'responses': ResponseSerializer(user_responses, many=True).data,
                'is_completed': completed_layers == total_layers,
                'last_updated': user_responses.aggregate(
                    Max('updated_at')
                )['updated_at__max']
            })

        serializer = ResponseSummarySerializer(summary_data, many=True)
        return DRFResponse(serializer.data)

    @action(detail=False, methods=['post'])
    def bulk_save(self, request):
        """Bulk save multiple responses (for localStorage sync)."""
        responses_data = request.data.get('responses', [])

        if not responses_data:
            return DRFResponse(
                {'error': 'No responses provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        created_responses = []
        errors = []

        for response_data in responses_data:
            serializer = self.get_serializer(data=response_data)
            if serializer.is_valid():
                self.perform_create(serializer)
                created_responses.append(serializer.data)
            else:
                errors.append({
                    'data': response_data,
                    'errors': serializer.errors
                })

        return DRFResponse({
            'created': len(created_responses),
            'failed': len(errors),
            'responses': created_responses,
            'errors': errors
        }, status=status.HTTP_201_CREATED if created_responses else status.HTTP_400_BAD_REQUEST)


class QuestionnaireProgressViewSet(viewsets.ModelViewSet):
    """ViewSet for managing questionnaire progress."""

    serializer_class = QuestionnaireProgressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return progress for the authenticated user."""
        return QuestionnaireProgress.objects.filter(
            user=self.request.user
        ).select_related('question')

    def perform_create(self, serializer):
        """Save progress with the current user."""
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'], url_path='by-question/(?P<question_id>[^/.]+)')
    def by_question(self, request, question_id=None):
        """Get progress for a specific question."""
        try:
            progress = self.get_queryset().get(question_id=question_id)
            serializer = self.get_serializer(progress)
            return DRFResponse(serializer.data)
        except QuestionnaireProgress.DoesNotExist:
            return DRFResponse(
                {'detail': 'Progress not found for this question'},
                status=status.HTTP_404_NOT_FOUND
            )
