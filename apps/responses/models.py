"""
AWFM Responses App - User Response Models

This module contains models for storing user responses to questions.
"""

import uuid
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.conf import settings


class Response(models.Model):
    """User response to a layer - stores selected options."""

    # Primary Key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Relations
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='responses',
        help_text=_('User who submitted this response')
    )
    question = models.ForeignKey(
        'content.Question',
        on_delete=models.CASCADE,
        related_name='responses',
        help_text=_('Question this response belongs to')
    )
    layer = models.ForeignKey(
        'content.Layer',
        on_delete=models.CASCADE,
        related_name='responses',
        help_text=_('Layer this response belongs to')
    )

    # Selected Options (supports multi-select)
    selected_option_ids = ArrayField(
        models.UUIDField(),
        help_text=_('Array of selected option UUIDs (supports multi-select)')
    )

    # Metadata
    completed_at = models.DateTimeField(
        _('completed at'),
        null=True,
        blank=True,
        help_text=_('When user confirmed this layer')
    )

    # Timestamps
    created_at = models.DateTimeField(
        _('created at'),
        default=timezone.now
    )
    updated_at = models.DateTimeField(
        _('updated at'),
        auto_now=True
    )

    class Meta:
        db_table = 'responses'
        verbose_name = _('response')
        verbose_name_plural = _('responses')
        unique_together = [['user', 'question', 'layer']]
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user'], name='idx_resp_user'),
            models.Index(fields=['question'], name='idx_resp_question'),
            models.Index(fields=['user', 'question'], name='idx_resp_user_q'),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.question.id} - L{self.layer.layer_number}"

    def mark_completed(self):
        """Mark this response as completed."""
        self.completed_at = timezone.now()
        self.save(update_fields=['completed_at'])


class QuestionnaireProgress(models.Model):
    """Track user progress through a questionnaire."""

    # Primary Key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Relations
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='questionnaire_progress'
    )
    question = models.ForeignKey(
        'content.Question',
        on_delete=models.CASCADE,
        related_name='user_progress'
    )

    # Progress Info
    current_phase = models.CharField(
        _('current phase'),
        max_length=50,
        help_text=_('Current flow phase (e.g., q1_selection, q2_review)')
    )
    current_layer = models.IntegerField(
        _('current layer'),
        default=1,
        help_text=_('Current layer number (1, 2, or 3)')
    )

    # Completion Status
    is_completed = models.BooleanField(
        _('is completed'),
        default=False
    )
    completed_at = models.DateTimeField(
        _('completed at'),
        null=True,
        blank=True
    )

    # Timestamps
    created_at = models.DateTimeField(_('created at'), default=timezone.now)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        db_table = 'questionnaire_progress'
        verbose_name = _('questionnaire progress')
        verbose_name_plural = _('questionnaire progress')
        unique_together = [['user', 'question']]
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user'], name='idx_prog_user'),
            models.Index(fields=['user', 'question'], name='idx_prog_user_q'),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.question.id} - {self.current_phase}"

    def mark_completed(self):
        """Mark questionnaire as completed."""
        self.is_completed = True
        self.completed_at = timezone.now()
        self.save(update_fields=['is_completed', 'completed_at'])
