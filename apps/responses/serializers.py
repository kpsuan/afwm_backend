"""
AWFM Responses App - Serializers
"""

from rest_framework import serializers
from .models import (
    Response, QuestionnaireProgress,
    Recording, RecordingReaction, RecordingComment, RecordingAffirmation
)
from apps.content.models import Question, Layer, Option
from apps.teams.models import Team


class ResponseSerializer(serializers.ModelSerializer):
    """Serializer for user responses."""

    # Read-only fields to include related data
    question_id = serializers.CharField(source='question.id', read_only=True)
    layer_number = serializers.IntegerField(source='layer.layer_number', read_only=True)

    # Write-only fields for creating responses
    question = serializers.CharField(write_only=True)
    layer_number_input = serializers.IntegerField(write_only=True, source='layer_number')

    # Explicitly define selected_option_ids as a list of UUIDs (not related objects)
    selected_option_ids = serializers.ListField(
        child=serializers.UUIDField(),
        help_text='Array of selected option UUIDs'
    )

    class Meta:
        model = Response
        fields = [
            'id',
            'user',
            'question',
            'question_id',
            'layer_number_input',
            'layer_number',
            'selected_option_ids',
            'completed_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def create(self, validated_data):
        """Create a response with proper FK resolution."""
        # Extract the question ID
        question_id = validated_data.pop('question')
        layer_number = validated_data.pop('layer_number')

        # Get the question and layer
        try:
            question = Question.objects.get(id=question_id)
            layer = Layer.objects.get(
                question=question,
                layer_number=layer_number
            )
        except (Question.DoesNotExist, Layer.DoesNotExist) as e:
            raise serializers.ValidationError({
                'detail': f'Question or layer not found: {str(e)}'
            })

        # Set the user from the request context
        user = self.context['request'].user

        # Update or create the response
        response, created = Response.objects.update_or_create(
            user=user,
            question=question,
            layer=layer,
            defaults={
                'selected_option_ids': validated_data['selected_option_ids'],
                'completed_at': validated_data.get('completed_at')
            }
        )

        return response

    def validate_selected_option_ids(self, value):
        """Validate that selected options exist."""
        if not value or len(value) == 0:
            raise serializers.ValidationError('At least one option must be selected')

        # Validate that all option IDs exist
        existing_count = Option.objects.filter(id__in=value).count()
        if existing_count != len(value):
            raise serializers.ValidationError('One or more selected options do not exist')

        return value


class QuestionnaireProgressSerializer(serializers.ModelSerializer):
    """Serializer for questionnaire progress tracking."""

    question_id = serializers.CharField(source='question.id', read_only=True)
    question = serializers.CharField(write_only=True)

    class Meta:
        model = QuestionnaireProgress
        fields = [
            'id',
            'user',
            'question',
            'question_id',
            'current_phase',
            'current_layer',
            'is_completed',
            'completed_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def create(self, validated_data):
        """Create or update progress."""
        question_id = validated_data.pop('question')

        try:
            question = Question.objects.get(id=question_id)
        except Question.DoesNotExist:
            raise serializers.ValidationError({'detail': 'Question not found'})

        user = self.context['request'].user

        # Update or create the progress
        progress, created = QuestionnaireProgress.objects.update_or_create(
            user=user,
            question=question,
            defaults={
                'current_phase': validated_data['current_phase'],
                'current_layer': validated_data.get('current_layer', 1),
                'is_completed': validated_data.get('is_completed', False),
                'completed_at': validated_data.get('completed_at')
            }
        )

        return progress


class ResponseSummarySerializer(serializers.Serializer):
    """Serializer for response summary (aggregated view)."""

    question_id = serializers.CharField()
    question_title = serializers.CharField()
    total_layers = serializers.IntegerField()
    completed_layers = serializers.IntegerField()
    responses = ResponseSerializer(many=True)
    is_completed = serializers.BooleanField()
    last_updated = serializers.DateTimeField()


# ==================== Recording Serializers ====================

class RecordingCommentSerializer(serializers.ModelSerializer):
    """Serializer for recording comments."""

    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_avatar = serializers.CharField(source='user.avatar_url', read_only=True)

    class Meta:
        model = RecordingComment
        fields = [
            'id', 'user', 'user_name', 'user_avatar',
            'recording', 'text', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class RecordingSerializer(serializers.ModelSerializer):
    """Serializer for recordings."""

    # Read-only computed fields
    user_name = serializers.SerializerMethodField()
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_avatar = serializers.SerializerMethodField()
    question_id = serializers.CharField(source='question.id', read_only=True)
    question_title = serializers.CharField(source='question.title', read_only=True)
    team_name = serializers.CharField(source='team.name', read_only=True)

    # Counts
    likes_count = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    affirmations_count = serializers.SerializerMethodField()

    # User interaction status
    user_has_liked = serializers.SerializerMethodField()
    user_has_affirmed = serializers.SerializerMethodField()

    # Write-only fields
    question = serializers.CharField(write_only=True)
    team_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = Recording
        fields = [
            'id', 'user', 'user_name', 'user_email', 'user_avatar',
            'question', 'question_id', 'question_title',
            'team', 'team_id', 'team_name',
            'recording_type', 'media_url', 'media_public_id',
            'thumbnail_url', 'text_content', 'description',
            'duration', 'file_size', 'is_visible_to_team',
            'likes_count', 'comments_count', 'affirmations_count',
            'user_has_liked', 'user_has_affirmed',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def get_user_name(self, obj):
        """Get user's display name with proper fallbacks."""
        if obj.user:
            # Try full_name first (first + last), then display_name, then email
            name = obj.user.full_name
            if name:
                return name
            if obj.user.display_name:
                return obj.user.display_name
            return obj.user.email
        return 'Unknown'

    def get_user_avatar(self, obj):
        """Get user's avatar URL."""
        if obj.user:
            return obj.user.profile_photo_url or None
        return None

    def get_likes_count(self, obj):
        return obj.reactions.count()

    def get_comments_count(self, obj):
        return obj.comments.count()

    def get_affirmations_count(self, obj):
        return obj.affirmations.count()

    def get_user_has_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.reactions.filter(user=request.user).exists()
        return False

    def get_user_has_affirmed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.affirmations.filter(affirming_user=request.user).exists()
        return False

    def create(self, validated_data):
        """Create a recording with proper FK resolution."""
        question_id = validated_data.pop('question')
        team_id = validated_data.pop('team_id', None)

        try:
            question = Question.objects.get(id=question_id)
        except Question.DoesNotExist:
            raise serializers.ValidationError({'question': 'Question not found'})

        team = None
        if team_id:
            try:
                team = Team.objects.get(id=team_id)
            except Team.DoesNotExist:
                raise serializers.ValidationError({'team_id': 'Team not found'})

        user = self.context['request'].user

        recording = Recording.objects.create(
            user=user,
            question=question,
            team=team,
            **validated_data
        )

        return recording


class RecordingUploadSerializer(serializers.Serializer):
    """Serializer for handling file uploads to Cloudinary."""

    file = serializers.FileField(required=True)
    recording_type = serializers.ChoiceField(choices=Recording.RecordingType.choices)
    question_id = serializers.CharField()
    team_id = serializers.UUIDField(required=False, allow_null=True)
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)


class RecordingTextSerializer(serializers.Serializer):
    """Serializer for creating text recordings (no file upload)."""

    text_content = serializers.CharField()
    question_id = serializers.CharField()
    team_id = serializers.UUIDField(required=False, allow_null=True)
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)


class RecordingListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing recordings."""

    user_name = serializers.SerializerMethodField()
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_avatar = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()

    class Meta:
        model = Recording
        fields = [
            'id', 'user', 'user_name', 'user_email', 'user_avatar',
            'recording_type', 'media_url', 'thumbnail_url',
            'description', 'duration', 'likes_count', 'created_at'
        ]

    def get_user_name(self, obj):
        """Get user's display name with proper fallbacks."""
        if obj.user:
            name = obj.user.full_name
            if name:
                return name
            if obj.user.display_name:
                return obj.user.display_name
            return obj.user.email
        return 'Unknown'

    def get_user_avatar(self, obj):
        """Get user's avatar URL."""
        if obj.user:
            return obj.user.profile_photo_url or None
        return None

    def get_likes_count(self, obj):
        return obj.reactions.count()


class RecordingReactionSerializer(serializers.ModelSerializer):
    """Serializer for recording reactions (likes)."""

    class Meta:
        model = RecordingReaction
        fields = ['id', 'user', 'recording', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']


class RecordingAffirmationSerializer(serializers.ModelSerializer):
    """Serializer for recording affirmations."""

    affirming_user_name = serializers.CharField(
        source='affirming_user.full_name', read_only=True
    )

    class Meta:
        model = RecordingAffirmation
        fields = ['id', 'affirming_user', 'affirming_user_name', 'recording', 'created_at']
        read_only_fields = ['id', 'affirming_user', 'created_at']
