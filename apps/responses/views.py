"""
AWFM Responses App - Views
"""

import cloudinary
import cloudinary.uploader
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response as DRFResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Count, Q, Max, Prefetch
from django.conf import settings
from .models import (
    Response, QuestionnaireProgress,
    Recording, RecordingReaction, RecordingComment, RecordingAffirmation
)
from .serializers import (
    ResponseSerializer,
    QuestionnaireProgressSerializer,
    ResponseSummarySerializer,
    RecordingSerializer,
    RecordingListSerializer,
    RecordingUploadSerializer,
    RecordingTextSerializer,
    RecordingCommentSerializer,
    RecordingReactionSerializer,
    RecordingAffirmationSerializer
)
from apps.content.models import Question
from apps.teams.models import Team
from apps.communication.notifications import notify_affirmation


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
        """Get summary of all user responses grouped by question.

        Optimized to avoid N+1 queries using Prefetch and annotations.
        """
        user = request.user

        # Prefetch only this user's responses with layer data
        user_responses_prefetch = Prefetch(
            'responses',
            queryset=Response.objects.filter(user=user).select_related('layer'),
            to_attr='user_responses'
        )

        # Get questions with annotations for layer count and prefetched responses
        questions = Question.objects.filter(
            responses__user=user
        ).distinct().prefetch_related(
            user_responses_prefetch
        ).annotate(
            total_layers=Count('layers', distinct=True)
        )

        summary_data = []

        for question in questions:
            # Use prefetched responses (no additional query)
            user_responses = question.user_responses

            # Count completed layers from prefetched data (no additional query)
            completed_layers = sum(
                1 for r in user_responses if r.completed_at is not None
            )

            # Get last updated from prefetched data (no additional query)
            last_updated = max(
                (r.updated_at for r in user_responses),
                default=None
            )

            summary_data.append({
                'question_id': question.id,
                'question_title': question.title,
                'total_layers': question.total_layers,
                'completed_layers': completed_layers,
                'responses': list(user_responses),  # Pass model instances, not serialized data
                'is_completed': completed_layers == question.total_layers,
                'last_updated': last_updated
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


class RecordingViewSet(viewsets.ModelViewSet):
    """ViewSet for managing recordings with Cloudinary upload support."""

    serializer_class = RecordingSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        """Return recordings based on filters."""
        queryset = Recording.objects.select_related(
            'user', 'question', 'team'
        ).prefetch_related('reactions', 'comments', 'affirmations')

        # Filter by team if specified
        team_id = self.request.query_params.get('team_id')
        if team_id:
            queryset = queryset.filter(team_id=team_id)

        # Filter by question if specified
        question_id = self.request.query_params.get('question_id')
        if question_id:
            queryset = queryset.filter(question_id=question_id)

        # Filter by user if specified (for viewing own recordings)
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        # Default: return recordings visible to user's teams or own recordings
        if not (team_id or question_id or user_id):
            user = self.request.user
            user_team_ids = user.team_memberships.values_list('team_id', flat=True)
            queryset = queryset.filter(
                Q(user=user) |
                (Q(team_id__in=user_team_ids) & Q(is_visible_to_team=True))
            )

        return queryset.order_by('-created_at')

    def get_serializer_class(self):
        if self.action == 'list':
            return RecordingListSerializer
        return RecordingSerializer

    def destroy(self, request, *args, **kwargs):
        """Delete a recording (only owner can delete)."""
        recording = self.get_object()

        # Check if user owns this recording
        if recording.user != request.user:
            return DRFResponse(
                {'error': 'You can only delete your own recordings'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Delete from Cloudinary if media exists
        if recording.media_public_id:
            try:
                resource_type = 'video' if recording.recording_type in ['video', 'audio'] else 'image'
                cloudinary.uploader.destroy(
                    recording.media_public_id,
                    resource_type=resource_type
                )
            except Exception as e:
                # Log but don't fail - we still want to delete the DB record
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f'Failed to delete Cloudinary resource: {e}')

        # Delete from database
        recording.delete()
        return DRFResponse(status=status.HTTP_204_NO_CONTENT)

    # Maximum file sizes (in bytes)
    MAX_VIDEO_SIZE = 100 * 1024 * 1024  # 100MB
    MAX_AUDIO_SIZE = 50 * 1024 * 1024   # 50MB

    @action(detail=False, methods=['post'], url_path='upload')
    def upload(self, request):
        """Upload a video or audio recording to Cloudinary."""
        serializer = RecordingUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return DRFResponse(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        file = serializer.validated_data['file']
        recording_type = serializer.validated_data['recording_type']

        # Validate file size
        max_size = self.MAX_VIDEO_SIZE if recording_type == 'video' else self.MAX_AUDIO_SIZE
        if file.size > max_size:
            max_mb = max_size // (1024 * 1024)
            return DRFResponse(
                {'error': f'File too large. Maximum size is {max_mb}MB.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        question_id = serializer.validated_data['question_id']
        team_id = serializer.validated_data.get('team_id')
        description = serializer.validated_data.get('description', '')

        # Validate question exists
        try:
            question = Question.objects.get(id=question_id)
        except Question.DoesNotExist:
            return DRFResponse(
                {'error': 'Question not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Validate team if provided
        team = None
        if team_id:
            try:
                team = Team.objects.get(id=team_id)
            except Team.DoesNotExist:
                return DRFResponse(
                    {'error': 'Team not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

        # Determine resource type for Cloudinary
        resource_type = 'video' if recording_type in ['video', 'audio'] else 'auto'

        try:
            # Upload to Cloudinary
            upload_result = cloudinary.uploader.upload(
                file,
                resource_type=resource_type,
                folder=f'awfm/recordings/{request.user.id}',
                public_id=f'{recording_type}_{question_id}_{int(request.user.id)}',
                overwrite=True,
                # Generate thumbnail for video
                eager=[{'format': 'jpg', 'transformation': [
                    {'width': 400, 'height': 600, 'crop': 'fill', 'gravity': 'auto'}
                ]}] if recording_type == 'video' else None
            )

            # Extract data from upload result
            media_url = upload_result.get('secure_url')
            media_public_id = upload_result.get('public_id')
            duration = upload_result.get('duration')
            file_size = upload_result.get('bytes')

            # Get thumbnail URL for video (with safe access)
            thumbnail_url = None
            if recording_type == 'video':
                eager_results = upload_result.get('eager')
                if eager_results and len(eager_results) > 0:
                    thumbnail_url = eager_results[0].get('secure_url')

            # Create recording
            recording = Recording.objects.create(
                user=request.user,
                question=question,
                team=team,
                recording_type=recording_type,
                media_url=media_url,
                media_public_id=media_public_id,
                thumbnail_url=thumbnail_url,
                description=description,
                duration=duration,
                file_size=file_size
            )

            response_serializer = RecordingSerializer(
                recording, context={'request': request}
            )
            return DRFResponse(response_serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return DRFResponse(
                {'error': f'Upload failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], url_path='text')
    def create_text(self, request):
        """Create a text recording (no file upload)."""
        serializer = RecordingTextSerializer(data=request.data)
        if not serializer.is_valid():
            return DRFResponse(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        question_id = serializer.validated_data['question_id']
        team_id = serializer.validated_data.get('team_id')
        text_content = serializer.validated_data['text_content']
        description = serializer.validated_data.get('description', '')

        # Validate question exists
        try:
            question = Question.objects.get(id=question_id)
        except Question.DoesNotExist:
            return DRFResponse(
                {'error': 'Question not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Validate team if provided
        team = None
        if team_id:
            try:
                team = Team.objects.get(id=team_id)
            except Team.DoesNotExist:
                return DRFResponse(
                    {'error': 'Team not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

        recording = Recording.objects.create(
            user=request.user,
            question=question,
            team=team,
            recording_type='text',
            text_content=text_content,
            description=description
        )

        response_serializer = RecordingSerializer(
            recording, context={'request': request}
        )
        return DRFResponse(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='like')
    def like(self, request, pk=None):
        """Toggle like on a recording."""
        recording = self.get_object()
        reaction, created = RecordingReaction.objects.get_or_create(
            user=request.user,
            recording=recording
        )

        if not created:
            # Already liked, so unlike
            reaction.delete()
            return DRFResponse({'liked': False, 'likes_count': recording.reactions.count()})

        return DRFResponse({'liked': True, 'likes_count': recording.reactions.count()})

    @action(detail=True, methods=['post'], url_path='affirm')
    def affirm(self, request, pk=None):
        """Toggle affirmation on a recording."""
        recording = self.get_object()

        # Can't affirm your own recording
        if recording.user == request.user:
            return DRFResponse(
                {'error': 'Cannot affirm your own recording'},
                status=status.HTTP_400_BAD_REQUEST
            )

        affirmation, created = RecordingAffirmation.objects.get_or_create(
            affirming_user=request.user,
            recording=recording
        )

        if not created:
            # Already affirmed, so remove affirmation
            affirmation.delete()
            return DRFResponse({
                'affirmed': False,
                'affirmations_count': recording.affirmations.count()
            })

        # Send notification to recording owner
        notify_affirmation(recording.user, request.user, recording)

        return DRFResponse({
            'affirmed': True,
            'affirmations_count': recording.affirmations.count()
        })

    @action(detail=True, methods=['get', 'post'], url_path='comments')
    def comments(self, request, pk=None):
        """Get or add comments on a recording."""
        recording = self.get_object()

        if request.method == 'GET':
            comments = recording.comments.select_related('user').all()
            serializer = RecordingCommentSerializer(comments, many=True)
            return DRFResponse(serializer.data)

        # POST - add a comment
        text = request.data.get('text')
        if not text:
            return DRFResponse(
                {'error': 'Comment text is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        comment = RecordingComment.objects.create(
            user=request.user,
            recording=recording,
            text=text
        )

        serializer = RecordingCommentSerializer(comment)
        return DRFResponse(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='my-recordings')
    def my_recordings(self, request):
        """Get all recordings by the current user."""
        recordings = Recording.objects.filter(user=request.user).select_related(
            'user', 'question', 'team'
        ).prefetch_related('reactions', 'comments', 'affirmations').order_by('-created_at')

        serializer = RecordingSerializer(
            recordings, many=True, context={'request': request}
        )
        return DRFResponse(serializer.data)

    @action(detail=False, methods=['get'], url_path='team/(?P<team_id>[^/.]+)')
    def team_recordings(self, request, team_id=None):
        """Get all recordings for a specific team."""
        recordings = Recording.objects.filter(
            team_id=team_id,
            is_visible_to_team=True
        ).select_related(
            'user', 'question', 'team'
        ).prefetch_related('reactions', 'comments', 'affirmations').order_by('-created_at')

        serializer = RecordingSerializer(
            recordings, many=True, context={'request': request}
        )
        return DRFResponse(serializer.data)
