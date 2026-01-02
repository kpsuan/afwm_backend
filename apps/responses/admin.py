"""
AWFM Responses App - Admin Configuration
"""

from django.contrib import admin
from .models import Response, QuestionnaireProgress


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
