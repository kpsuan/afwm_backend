"""
AWFM Content App - Django Admin Configuration

Registers content models in Django admin interface with image upload support.
"""

import cloudinary
import cloudinary.uploader
from django import forms
from django.contrib import admin
from django.conf import settings
from django.utils.html import format_html
from apps.content.models import (
    Question,
    Layer,
    Option,
    Component,
    PersonalPatternRecognition
)


# ==================== Image Upload Mixin ====================

class CloudinaryImageMixin:
    """Mixin to handle Cloudinary image uploads in admin."""

    def upload_to_cloudinary(self, image_file, folder='awfm'):
        """Upload image to Cloudinary and return URL."""
        cloudinary_config = getattr(settings, 'CLOUDINARY_STORAGE', {})
        if not cloudinary_config.get('CLOUD_NAME'):
            return None, None

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

        # Generate thumbnail
        thumbnail_url = cloudinary.utils.cloudinary_url(
            public_id,
            width=400,
            height=300,
            crop='fill',
            quality='auto:good',
            fetch_format='auto'
        )[0]

        return image_url, thumbnail_url


# ==================== Custom Forms ====================

class QuestionAdminForm(forms.ModelForm):
    """Form for Question with image upload."""
    image_upload = forms.ImageField(
        required=False,
        label='Upload New Image',
        help_text='Upload a new image (JPG, PNG, GIF, WebP). Max 10MB.'
    )

    class Meta:
        model = Question
        fields = '__all__'


class LayerAdminForm(forms.ModelForm):
    """Form for Layer with image upload."""
    image_upload = forms.ImageField(
        required=False,
        label='Upload New Image',
        help_text='Upload a new image (JPG, PNG, GIF, WebP). Max 10MB.'
    )

    class Meta:
        model = Layer
        fields = '__all__'


class ComponentAdminForm(forms.ModelForm):
    """Form for Component with image upload."""
    image_upload = forms.ImageField(
        required=False,
        label='Upload New Image',
        help_text='Upload a new image (JPG, PNG, GIF, WebP). Max 10MB.'
    )

    class Meta:
        model = Component
        fields = '__all__'


# ==================== Inline Admins ====================

class ComponentInline(admin.TabularInline):
    """Inline admin for components within an option."""
    model = Component
    extra = 0
    fields = ['component_type', 'component_text', 'character_count']
    readonly_fields = ['character_count']


class OptionInline(admin.TabularInline):
    """Inline admin for options within a layer."""
    model = Option
    extra = 0
    fields = ['option_number', 'option_text', 'display_order']
    show_change_link = True


class LayerInline(admin.StackedInline):
    """Inline admin for layers within a question."""
    model = Layer
    extra = 0
    fields = [
        'layer_number',
        'layer_title',
        'layer_question',
        'selection_type',
        'max_selections',
        'components_at_selection',
        'components_at_confirmation'
    ]
    show_change_link = True


# ==================== Model Admins ====================

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin, CloudinaryImageMixin):
    """Admin for Question model with image upload."""

    form = QuestionAdminForm

    list_display = [
        'id',
        'title',
        'category',
        'batch_number',
        'display_order',
        'is_active',
        'image_preview_list',
        'created_at'
    ]
    list_filter = ['batch_number', 'category', 'is_active']
    search_fields = ['id', 'title', 'question_text']
    ordering = ['display_order']

    fieldsets = [
        ('Question Info', {
            'fields': ['id', 'title', 'question_text', 'category']
        }),
        ('Organization', {
            'fields': ['display_order', 'batch_number', 'uhcda_section']
        }),
        ('Image', {
            'fields': ['image_preview', 'image_upload', 'image_url', 'thumbnail_url'],
            'description': 'Upload an image for this question card.'
        }),
        ('Status', {
            'fields': ['is_active']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]
    readonly_fields = ['created_at', 'updated_at', 'image_preview']

    inlines = [LayerInline]

    def image_preview(self, obj):
        """Show large image preview."""
        if obj.image_url:
            return format_html(
                '<img src="{}" style="max-width: 400px; max-height: 300px; border-radius: 8px;" />',
                obj.thumbnail_url or obj.image_url
            )
        return "No image uploaded"
    image_preview.short_description = 'Current Image'

    def image_preview_list(self, obj):
        """Show small image preview in list."""
        if obj.thumbnail_url or obj.image_url:
            return format_html(
                '<img src="{}" style="width: 60px; height: 45px; object-fit: cover; border-radius: 4px;" />',
                obj.thumbnail_url or obj.image_url
            )
        return "-"
    image_preview_list.short_description = 'Image'

    def save_model(self, request, obj, form, change):
        """Handle image upload on save."""
        image_file = form.cleaned_data.get('image_upload')
        if image_file:
            folder = f'awfm/questions/{obj.id}'
            image_url, thumbnail_url = self.upload_to_cloudinary(image_file, folder)
            if image_url:
                obj.image_url = image_url
                obj.thumbnail_url = thumbnail_url
        super().save_model(request, obj, form, change)


@admin.register(Layer)
class LayerAdmin(admin.ModelAdmin, CloudinaryImageMixin):
    """Admin for Layer model with image upload."""

    form = LayerAdminForm

    list_display = [
        'question',
        'layer_number',
        'layer_title',
        'selection_type',
        'max_selections',
        'image_preview_list',
        'created_at'
    ]
    list_filter = ['question', 'layer_number', 'selection_type']
    search_fields = ['layer_title', 'layer_question']
    ordering = ['question', 'layer_number']

    fieldsets = [
        ('Layer Info', {
            'fields': [
                'question',
                'layer_number',
                'layer_title',
                'layer_question'
            ]
        }),
        ('Selection Settings', {
            'fields': ['selection_type', 'max_selections']
        }),
        ('Component Display', {
            'fields': ['components_at_selection', 'components_at_confirmation']
        }),
        ('Image', {
            'fields': ['image_preview', 'image_upload', 'image_url'],
            'description': 'Upload an image for this layer.'
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]
    readonly_fields = ['created_at', 'updated_at', 'image_preview']

    inlines = [OptionInline]

    def image_preview(self, obj):
        """Show image preview."""
        if obj.image_url:
            return format_html(
                '<img src="{}" style="max-width: 400px; max-height: 300px; border-radius: 8px;" />',
                obj.image_url
            )
        return "No image uploaded"
    image_preview.short_description = 'Current Image'

    def image_preview_list(self, obj):
        """Show small image preview in list."""
        if obj.image_url:
            return format_html(
                '<img src="{}" style="width: 60px; height: 45px; object-fit: cover; border-radius: 4px;" />',
                obj.image_url
            )
        return "-"
    image_preview_list.short_description = 'Image'

    def save_model(self, request, obj, form, change):
        """Handle image upload on save."""
        image_file = form.cleaned_data.get('image_upload')
        if image_file:
            folder = f'awfm/layers/{obj.question_id}_L{obj.layer_number}'
            image_url, _ = self.upload_to_cloudinary(image_file, folder)
            if image_url:
                obj.image_url = image_url
        super().save_model(request, obj, form, change)


@admin.register(Option)
class OptionAdmin(admin.ModelAdmin):
    """Admin for Option model."""

    list_display = [
        'question',
        'option_number',
        'option_text_preview',
        'layer',
        'display_order',
        'component_count'
    ]
    list_filter = ['question', 'layer']
    search_fields = ['option_text']
    ordering = ['question', 'display_order']

    fieldsets = [
        ('Option Info', {
            'fields': ['question', 'layer', 'option_number', 'option_text']
        }),
        ('Display', {
            'fields': ['display_order']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]
    readonly_fields = ['created_at', 'updated_at']

    inlines = [ComponentInline]

    def option_text_preview(self, obj):
        """Show truncated option text."""
        return obj.option_text[:60] + '...' if len(obj.option_text) > 60 else obj.option_text
    option_text_preview.short_description = 'Option Text'

    def component_count(self, obj):
        """Show count of components for this option."""
        return obj.components.count()
    component_count.short_description = 'Components'


@admin.register(Component)
class ComponentAdmin(admin.ModelAdmin, CloudinaryImageMixin):
    """Admin for Component model with image upload."""

    form = ComponentAdminForm

    list_display = [
        'option',
        'component_type',
        'text_preview',
        'character_count',
        'media_type',
        'image_preview_list',
        'created_at'
    ]
    list_filter = ['component_type', 'media_type', 'option__question']
    search_fields = ['component_text']
    ordering = ['option', 'component_type']

    fieldsets = [
        ('Component Info', {
            'fields': ['option', 'component_type', 'component_text']
        }),
        ('Media', {
            'fields': ['image_preview', 'image_upload', 'image_url', 'media_type'],
            'description': 'Upload media for this component.'
        }),
        ('Metadata', {
            'fields': ['character_count']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]
    readonly_fields = ['character_count', 'created_at', 'updated_at', 'image_preview']

    def text_preview(self, obj):
        """Show truncated component text."""
        return obj.component_text[:80] + '...' if len(obj.component_text) > 80 else obj.component_text
    text_preview.short_description = 'Text'

    def image_preview(self, obj):
        """Show image preview."""
        if obj.image_url:
            return format_html(
                '<img src="{}" style="max-width: 400px; max-height: 300px; border-radius: 8px;" />',
                obj.image_url
            )
        return "No image uploaded"
    image_preview.short_description = 'Current Image'

    def image_preview_list(self, obj):
        """Show small image preview in list."""
        if obj.image_url:
            return format_html(
                '<img src="{}" style="width: 40px; height: 30px; object-fit: cover; border-radius: 4px;" />',
                obj.image_url
            )
        return "-"
    image_preview_list.short_description = 'Image'

    def save_model(self, request, obj, form, change):
        """Handle image upload on save."""
        image_file = form.cleaned_data.get('image_upload')
        if image_file:
            folder = f'awfm/components/{obj.option.question_id}_{obj.component_type}'
            image_url, _ = self.upload_to_cloudinary(image_file, folder)
            if image_url:
                obj.image_url = image_url
                obj.media_type = 'image'
        super().save_model(request, obj, form, change)


@admin.register(PersonalPatternRecognition)
class PPRAdmin(admin.ModelAdmin):
    """Admin for PersonalPatternRecognition model."""

    list_display = [
        'question',
        'pattern_name',
        'l1_option',
        'l2_options_display',
        'l3_option',
        'character_count',
        'coverage_percentage'
    ]
    list_filter = ['question']
    search_fields = ['pattern_name', 'ppr_text']
    ordering = ['question', 'pattern_name']

    fieldsets = [
        ('Pattern Info', {
            'fields': ['question', 'pattern_name']
        }),
        ('Selection Pattern', {
            'fields': ['l1_option', 'l2_options', 'l3_option']
        }),
        ('PPR Text', {
            'fields': ['ppr_text']
        }),
        ('Metadata', {
            'fields': ['character_count', 'coverage_percentage']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]
    readonly_fields = ['character_count', 'created_at', 'updated_at']

    def l2_options_display(self, obj):
        """Display L2 options as comma-separated string."""
        return ', '.join(map(str, obj.l2_options))
    l2_options_display.short_description = 'L2 Options'
