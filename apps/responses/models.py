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


class Recording(models.Model):
    """User recording (video, audio, or text) to explain their response."""

    class RecordingType(models.TextChoices):
        VIDEO = 'video', _('Video')
        AUDIO = 'audio', _('Audio')
        TEXT = 'text', _('Text')

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
        related_name='recordings',
        help_text=_('User who created this recording')
    )
    question = models.ForeignKey(
        'content.Question',
        on_delete=models.CASCADE,
        related_name='recordings',
        help_text=_('Question this recording is for')
    )
    team = models.ForeignKey(
        'teams.Team',
        on_delete=models.CASCADE,
        related_name='recordings',
        null=True,
        blank=True,
        help_text=_('Team this recording belongs to')
    )

    # Recording Type
    recording_type = models.CharField(
        _('recording type'),
        max_length=10,
        choices=RecordingType.choices,
        default=RecordingType.VIDEO
    )

    # Media Content (for video/audio)
    media_url = models.URLField(
        _('media URL'),
        max_length=500,
        blank=True,
        null=True,
        help_text=_('Cloudinary URL for video/audio file')
    )
    media_public_id = models.CharField(
        _('media public ID'),
        max_length=255,
        blank=True,
        null=True,
        help_text=_('Cloudinary public ID for media management')
    )
    thumbnail_url = models.URLField(
        _('thumbnail URL'),
        max_length=500,
        blank=True,
        null=True,
        help_text=_('Thumbnail image URL (for video)')
    )

    # Text Content (for text type)
    text_content = models.TextField(
        _('text content'),
        blank=True,
        null=True,
        help_text=_('Text response content')
    )

    # Description/Caption
    description = models.CharField(
        _('description'),
        max_length=500,
        blank=True,
        null=True,
        help_text=_('Short description or caption')
    )

    # Media Metadata
    duration = models.FloatField(
        _('duration'),
        blank=True,
        null=True,
        help_text=_('Duration in seconds (for video/audio)')
    )
    file_size = models.PositiveIntegerField(
        _('file size'),
        blank=True,
        null=True,
        help_text=_('File size in bytes')
    )

    # Visibility
    is_visible_to_team = models.BooleanField(
        _('visible to team'),
        default=True,
        help_text=_('Whether team members can see this recording')
    )

    # Timestamps
    created_at = models.DateTimeField(_('created at'), default=timezone.now)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        db_table = 'recordings'
        verbose_name = _('recording')
        verbose_name_plural = _('recordings')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user'], name='idx_rec_user'),
            models.Index(fields=['question'], name='idx_rec_question'),
            models.Index(fields=['team'], name='idx_rec_team'),
            models.Index(fields=['user', 'question'], name='idx_rec_user_q'),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.recording_type} - {self.question.id}"


class RecordingReaction(models.Model):
    """Reaction (like) to a recording."""

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
        related_name='recording_reactions'
    )
    recording = models.ForeignKey(
        Recording,
        on_delete=models.CASCADE,
        related_name='reactions'
    )

    # Timestamps
    created_at = models.DateTimeField(_('created at'), default=timezone.now)

    class Meta:
        db_table = 'recording_reactions'
        verbose_name = _('recording reaction')
        verbose_name_plural = _('recording reactions')
        unique_together = [['user', 'recording']]

    def __str__(self):
        return f"{self.user.email} liked {self.recording.id}"


class RecordingComment(models.Model):
    """Comment on a recording."""

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
        related_name='recording_comments'
    )
    recording = models.ForeignKey(
        Recording,
        on_delete=models.CASCADE,
        related_name='comments'
    )

    # Content
    text = models.TextField(_('comment text'))

    # Timestamps
    created_at = models.DateTimeField(_('created at'), default=timezone.now)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        db_table = 'recording_comments'
        verbose_name = _('recording comment')
        verbose_name_plural = _('recording comments')
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user.email} on {self.recording.id}"


class RecordingAffirmation(models.Model):
    """Affirmation of commitment to a user's recording/decisions."""

    # Primary Key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Relations
    affirming_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='affirmations_given',
        help_text=_('User giving the affirmation')
    )
    recording = models.ForeignKey(
        Recording,
        on_delete=models.CASCADE,
        related_name='affirmations'
    )

    # Timestamps
    created_at = models.DateTimeField(_('created at'), default=timezone.now)

    class Meta:
        db_table = 'recording_affirmations'
        verbose_name = _('recording affirmation')
        verbose_name_plural = _('recording affirmations')
        unique_together = [['affirming_user', 'recording']]

    def __str__(self):
        return f"{self.affirming_user.email} affirmed {self.recording.user.email}"
