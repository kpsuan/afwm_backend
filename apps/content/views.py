"""
AWFM Content App - Views

API ViewSets for content models.
"""

import cloudinary
import cloudinary.uploader
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from django.conf import settings

from apps.content.models import (
    Question,
    Layer,
    Option,
    Component,
    PersonalPatternRecognition
)
from apps.content.serializers import (
    QuestionSerializer,
    QuestionListSerializer,
    LayerSerializer,
    OptionSerializer,
    ComponentSerializer,
    PPRSerializer
)


class QuestionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for Questions.

    GET /api/v1/content/questions/ - List all questions
    GET /api/v1/content/questions/{id}/ - Get question with full nested data
    GET /api/v1/content/questions/{id}/layers/ - Get layers for question
    GET /api/v1/content/questions/{id}/ppr-patterns/ - Get PPR patterns for question
    """

    permission_classes = [AllowAny]  # Public read access for content
    queryset = Question.objects.filter(is_active=True).prefetch_related(
        'layers__options__components',
        'ppr_patterns'
    )
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['batch_number', 'category', 'is_active']
    ordering_fields = ['display_order', 'created_at']
    ordering = ['display_order']

    def get_serializer_class(self):
        """Use lightweight serializer for list, full serializer for detail."""
        if self.action == 'list':
            return QuestionListSerializer
        return QuestionSerializer

    @action(detail=True, methods=['get'])
    def layers(self, request, pk=None):
        """Get layers for a specific question."""
        question = self.get_object()
        layers = question.layers.all()
        serializer = LayerSerializer(layers, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='ppr-patterns')
    def ppr_patterns(self, request, pk=None):
        """Get PPR patterns for a specific question."""
        question = self.get_object()
        patterns = question.ppr_patterns.all()
        serializer = PPRSerializer(patterns, many=True)
        return Response(serializer.data)


class LayerViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for Layers.

    GET /api/v1/content/layers/ - List all layers
    GET /api/v1/content/layers/{id}/ - Get layer with options
    """

    permission_classes = [AllowAny]
    queryset = Layer.objects.all().prefetch_related('options__components')
    serializer_class = LayerSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['question', 'layer_number', 'selection_type']
    ordering_fields = ['layer_number', 'created_at']
    ordering = ['question', 'layer_number']


class OptionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for Options.

    GET /api/v1/content/options/ - List all options
    GET /api/v1/content/options/{id}/ - Get option with components
    """

    permission_classes = [AllowAny]
    queryset = Option.objects.all().prefetch_related('components')
    serializer_class = OptionSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['question', 'layer', 'option_number']
    ordering_fields = ['option_number', 'display_order', 'created_at']
    ordering = ['display_order']


class ComponentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for Components.

    GET /api/v1/content/components/ - List all components
    GET /api/v1/content/components/{id}/ - Get component detail
    """

    permission_classes = [AllowAny]
    queryset = Component.objects.all()
    serializer_class = ComponentSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['option', 'component_type']
    ordering_fields = ['component_type', 'created_at']
    ordering = ['option', 'component_type']


class PPRViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for Personal Pattern Recognition.

    GET /api/v1/content/ppr/ - List all PPR patterns
    GET /api/v1/content/ppr/{id}/ - Get PPR pattern detail
    """

    permission_classes = [AllowAny]
    queryset = PersonalPatternRecognition.objects.all()
    serializer_class = PPRSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['question', 'l1_option', 'l3_option']
    ordering = ['question', 'pattern_name']


class ImageUploadView(APIView):
    """
    API endpoint for uploading images to Cloudinary.

    POST /api/v1/content/upload-image/
    - Upload an image and get back the Cloudinary URL
    - Optionally attach to a question, layer, or component
    """

    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]

    ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

    def post(self, request):
        """Upload an image to Cloudinary."""
        cloudinary_config = getattr(settings, 'CLOUDINARY_STORAGE', {})
        if not cloudinary_config.get('CLOUD_NAME'):
            return Response(
                {'error': 'Cloudinary is not configured'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        if 'image' not in request.FILES:
            return Response(
                {'error': 'No image file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        image_file = request.FILES['image']

        if image_file.content_type not in self.ALLOWED_TYPES:
            return Response(
                {'error': f'Invalid file type. Allowed: {", ".join(self.ALLOWED_TYPES)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if image_file.size > self.MAX_FILE_SIZE:
            return Response(
                {'error': 'File too large. Maximum size: 10MB'},
                status=status.HTTP_400_BAD_REQUEST
            )

        content_type = request.data.get('content_type')
        content_id = request.data.get('content_id')
        folder = request.data.get('folder', 'awfm')

        if content_type and content_id:
            folder = f'awfm/{content_type}s/{content_id}'

        try:
            cloudinary.config(
                cloud_name=cloudinary_config['CLOUD_NAME'],
                api_key=cloudinary_config['API_KEY'],
                api_secret=cloudinary_config['API_SECRET'],
            )

            result = cloudinary.uploader.upload(
                image_file,
                folder=folder,
                resource_type='image',
                transformation=[
                    {'quality': 'auto:good'},
                    {'fetch_format': 'auto'}
                ]
            )

            image_url = result['secure_url']
            public_id = result['public_id']

            thumbnail_url = cloudinary.utils.cloudinary_url(
                public_id,
                width=400,
                height=300,
                crop='fill',
                quality='auto:good',
                fetch_format='auto'
            )[0]

            if content_type and content_id:
                self._update_content_image(content_type, content_id, image_url, thumbnail_url)

            return Response({
                'url': image_url,
                'thumbnail_url': thumbnail_url,
                'public_id': public_id,
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {'error': f'Upload failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _update_content_image(self, content_type, content_id, image_url, thumbnail_url=None):
        """Update the image_url field on the specified content."""
        try:
            if content_type == 'question':
                obj = Question.objects.get(pk=content_id)
                obj.image_url = image_url
                if thumbnail_url:
                    obj.thumbnail_url = thumbnail_url
                obj.save()
            elif content_type == 'layer':
                obj = Layer.objects.get(pk=content_id)
                obj.image_url = image_url
                obj.save()
            elif content_type == 'component':
                obj = Component.objects.get(pk=content_id)
                obj.image_url = image_url
                obj.media_type = 'image'
                obj.save()
        except (Question.DoesNotExist, Layer.DoesNotExist, Component.DoesNotExist):
            pass
