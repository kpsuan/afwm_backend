"""
AWFM Responses App - Serializers
"""

from rest_framework import serializers
from .models import Response, QuestionnaireProgress
from apps.content.models import Question, Layer, Option


class ResponseSerializer(serializers.ModelSerializer):
    """Serializer for user responses."""

    # Read-only fields to include related data
    question_id = serializers.CharField(source='question.id', read_only=True)
    layer_number = serializers.IntegerField(source='layer.layer_number', read_only=True)

    # Write-only fields for creating responses
    question = serializers.CharField(write_only=True)
    layer_number_input = serializers.IntegerField(write_only=True, source='layer_number')

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
