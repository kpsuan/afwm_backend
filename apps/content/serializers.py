"""
AWFM Content App - Serializers

Serializers for converting content models to/from JSON.
"""

from rest_framework import serializers
from apps.content.models import (
    Question,
    Layer,
    Option,
    Component,
    PersonalPatternRecognition
)


class ComponentSerializer(serializers.ModelSerializer):
    """Serializer for Component model (C1-C11)."""

    class Meta:
        model = Component
        fields = [
            'id',
            'component_type',
            'component_text',
            'character_count',
            'image_url',
            'media_type',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'character_count', 'created_at', 'updated_at']


class OptionSerializer(serializers.ModelSerializer):
    """Serializer for Option model with nested components."""

    # Nested components
    components = ComponentSerializer(many=True, read_only=True)

    class Meta:
        model = Option
        fields = [
            'id',
            'option_number',
            'option_text',
            'display_order',
            'image_url',
            'components',  # Nested
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class LayerSerializer(serializers.ModelSerializer):
    """Serializer for Layer model with nested options."""

    # Nested options
    options = OptionSerializer(many=True, read_only=True)

    class Meta:
        model = Layer
        fields = [
            'id',
            'layer_number',
            'layer_title',
            'layer_question',
            'selection_type',
            'max_selections',
            'components_at_selection',
            'components_at_confirmation',
            'image_url',
            'options',  # Nested
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PPRSerializer(serializers.ModelSerializer):
    """Serializer for Personal Pattern Recognition."""

    class Meta:
        model = PersonalPatternRecognition
        fields = [
            'id',
            'pattern_name',
            'l1_option',
            'l2_options',
            'l3_option',
            'ppr_text',
            'character_count',
            'coverage_percentage',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'character_count', 'created_at', 'updated_at']


class QuestionSerializer(serializers.ModelSerializer):
    """Serializer for Question model with nested layers and PPR patterns."""

    # Nested layers and PPR
    layers = LayerSerializer(many=True, read_only=True)
    ppr_patterns = PPRSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = [
            'id',
            'title',
            'question_text',
            'category',
            'display_order',
            'batch_number',
            'uhcda_section',
            'is_active',
            'image_url',
            'thumbnail_url',
            'layers',  # Nested
            'ppr_patterns',  # Nested
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class QuestionListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for question list (without nested data)."""

    class Meta:
        model = Question
        fields = [
            'id',
            'title',
            'question_text',
            'category',
            'display_order',
            'batch_number',
            'is_active',
            'image_url',
            'thumbnail_url'
        ]
        read_only_fields = ['id']
