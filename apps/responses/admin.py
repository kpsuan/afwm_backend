"""
AWFM Responses App - Admin Configuration
"""

from django.contrib import admin
from .models import (
    Response, QuestionnaireProgress,
    Recording, RecordingReaction, RecordingComment, RecordingAffirmation
)


@admin.register(Response)
class ResponseAdmin(admin.ModelAdmin):
    """Admin for Response model."""

    list_display = ('user', 'question', 'layer', 'completed_at', 'created_at')
    list_filter = ('completed_at', 'created_at', 'question')
    search_fields = ('user__email', 'question__id', 'question__title')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('-created_at',)

    fieldsets = (
        (None, {
            'fields': ('id', 'user', 'question', 'layer')
        }),
        ('Response Data', {
            'fields': ('selected_option_ids', 'completed_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(QuestionnaireProgress)
class QuestionnaireProgressAdmin(admin.ModelAdmin):
    """Admin for QuestionnaireProgress model."""

    list_display = ('user', 'question', 'current_phase', 'current_layer', 'is_completed', 'updated_at')
    list_filter = ('is_completed', 'current_layer', 'question')
    search_fields = ('user__email', 'question__id', 'question__title')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('-updated_at',)

    fieldsets = (
        (None, {
            'fields': ('id', 'user', 'question')
        }),
        ('Progress', {
            'fields': ('current_phase', 'current_layer', 'is_completed', 'completed_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(Recording)
class RecordingAdmin(admin.ModelAdmin):
    """Admin for Recording model."""

    list_display = ('user', 'recording_type', 'question', 'team', 'is_visible_to_team', 'created_at')
    list_filter = ('recording_type', 'is_visible_to_team', 'created_at', 'team')
    search_fields = ('user__email', 'question__title', 'description')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('-created_at',)

    fieldsets = (
        (None, {
            'fields': ('id', 'user', 'question', 'team')
        }),
        ('Recording Content', {
            'fields': ('recording_type', 'media_url', 'media_public_id', 'thumbnail_url', 'text_content')
        }),
        ('Metadata', {
            'fields': ('description', 'duration', 'file_size', 'is_visible_to_team')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(RecordingReaction)
class RecordingReactionAdmin(admin.ModelAdmin):
    """Admin for RecordingReaction model."""

    list_display = ('user', 'recording', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__email',)
    readonly_fields = ('id', 'created_at')


@admin.register(RecordingComment)
class RecordingCommentAdmin(admin.ModelAdmin):
    """Admin for RecordingComment model."""

    list_display = ('user', 'recording', 'text', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__email', 'text')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(RecordingAffirmation)
class RecordingAffirmationAdmin(admin.ModelAdmin):
    """Admin for RecordingAffirmation model."""

    list_display = ('affirming_user', 'recording', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('affirming_user__email',)
    readonly_fields = ('id', 'created_at')
