"""
AWFM Content App - Question Content Models

This module contains models for the question content hierarchy:
- Question - The 30 questions (4 for Pre-MVP)
- Layer - 3 layers per question (L1, L2, L3)
- Option - ~11 options per question
- Component - C1-C11 components for each option
- PersonalPatternRecognition (PPR) - Synthesis texts
"""

import uuid
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Question(models.Model):
    """Question model - The 30 AWFM questions."""

    # Primary Key
    id = models.CharField(
        primary_key=True,
        max_length=10,
        help_text=_('Question ID (e.g., Q10A, Q10B, Q11, Q12)')
    )

    # Question Info
    title = models.CharField(
        _('title'),
        max_length=255,
        help_text=_('Short question title')
    )
    question_text = models.TextField(
        _('question text'),
        help_text=_('The actual question asked to users')
    )
    category = models.CharField(
        _('category'),
        max_length=50,
        blank=True,
        default='',
        help_text=_('Question category (e.g., UHCDA Priority Values)')
    )

    # Question Order
    display_order = models.IntegerField(
        _('display order'),
        help_text=_('Order in which question appears')
    )
    batch_number = models.IntegerField(
        _('batch number'),
        help_text=_('Which batch this question belongs to (1-10)')
    )

    # UHCDA Section Reference
    uhcda_section = models.CharField(
        _('UHCDA section'),
        max_length=50,
        blank=True,
        default='',
        help_text=_('UHCDA legal section reference')
    )

    # Status
    is_active = models.BooleanField(
        _('is active'),
        default=True,
        help_text=_('Whether this question is active')
    )

    # Media
    image_url = models.TextField(
        _('image URL'),
        blank=True,
        default='',
        help_text=_('Cloudinary URL for question card image')
    )
    thumbnail_url = models.TextField(
        _('thumbnail URL'),
        blank=True,
        default='',
        help_text=_('Cloudinary URL for question thumbnail (auto-generated)')
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
        db_table = 'questions'
        verbose_name = _('question')
        verbose_name_plural = _('questions')
        ordering = ['display_order']
        indexes = [
            models.Index(fields=['batch_number'], name='idx_q_batch'),
            models.Index(fields=['display_order'], name='idx_q_order'),
        ]

    def __str__(self):
        return f"{self.id}: {self.title}"


class Layer(models.Model):
    """Layer model - 3 layers per question (L1, L2, L3)."""

    # Primary Key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Relations
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='layers'
    )

    # Layer Info
    layer_number = models.IntegerField(
        _('layer number'),
        validators=[MinValueValidator(1), MaxValueValidator(3)],
        help_text=_('Layer number (1, 2, or 3)')
    )
    layer_title = models.CharField(
        _('layer title'),
        max_length=255,
        help_text=_('e.g., YOUR POSITION, YOUR CHALLENGES, YOUR MIND-CHANGER')
    )
    layer_question = models.TextField(
        _('layer question'),
        help_text=_('The question text for this layer')
    )

    # Selection Type
    SELECTION_SINGLE = 'single'
    SELECTION_MULTI = 'multi'

    SELECTION_CHOICES = [
        (SELECTION_SINGLE, _('Single-select')),
        (SELECTION_MULTI, _('Multi-select')),
    ]

    selection_type = models.CharField(
        _('selection type'),
        max_length=20,
        choices=SELECTION_CHOICES
    )
    max_selections = models.IntegerField(
        _('max selections'),
        null=True,
        blank=True,
        help_text=_('Maximum selections for multi-select (e.g., 2)')
    )

    # Components Shown
    components_at_selection = ArrayField(
        models.CharField(max_length=5),
        default=list,
        help_text=_('Components shown at selection (e.g., [C1, C3])')
    )
    components_at_confirmation = ArrayField(
        models.CharField(max_length=5),
        default=list,
        help_text=_('Components shown at confirmation (e.g., [C2, C4, C5])')
    )

    # Media
    image_url = models.TextField(
        _('image URL'),
        blank=True,
        default='',
        help_text=_('Cloudinary URL for layer image')
    )

    # Timestamps
    created_at = models.DateTimeField(_('created at'), default=timezone.now)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        db_table = 'layers'
        verbose_name = _('layer')
        verbose_name_plural = _('layers')
        unique_together = [['question', 'layer_number']]
        ordering = ['question', 'layer_number']
        indexes = [
            models.Index(fields=['question'], name='idx_layer_question'),
        ]

    def __str__(self):
        return f"{self.question.id} - L{self.layer_number}: {self.layer_title}"


class Option(models.Model):
    """Option model - Options for each layer."""

    # Primary Key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Relations
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='options'
    )
    layer = models.ForeignKey(
        Layer,
        on_delete=models.CASCADE,
        related_name='options'
    )

    # Option Info
    option_number = models.IntegerField(
        _('option number'),
        help_text=_('Option number within question (1-11)')
    )
    option_text = models.TextField(
        _('option text'),
        help_text=_('C1 text - Form Response Option')
    )

    # Display
    display_order = models.IntegerField(_('display order'))

    # Media
    image_url = models.TextField(
        _('image URL'),
        blank=True,
        default='',
        help_text=_('Cloudinary URL for option card image')
    )

    # Timestamps
    created_at = models.DateTimeField(_('created at'), default=timezone.now)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        db_table = 'options'
        verbose_name = _('option')
        verbose_name_plural = _('options')
        unique_together = [['question', 'option_number']]
        ordering = ['display_order']
        indexes = [
            models.Index(fields=['question'], name='idx_opt_question'),
            models.Index(fields=['layer'], name='idx_opt_layer'),
            models.Index(fields=['display_order'], name='idx_opt_order'),
        ]

    def __str__(self):
        return f"{self.question.id} - Option {self.option_number}"


class Component(models.Model):
    """Component model - C1-C11 components for each option."""

    # Component type choices
    COMPONENT_CHOICES = [
        ('C1', _('C1: Form Response Option')),
        ('C2', _('C2: Why This Matters')),
        ('C3', _('C3: How This Sounds')),
        ('C4', _('C4: Research Evidence')),
        ('C5', _('C5: Decision Impact')),
        ('C6', _('C6: What You\'re Fighting For')),
        ('C7', _('C7: Cooperative Learning')),
        ('C8', _('C8: Interdependency at Work')),
        ('C9', _('C9: Barriers to Access')),
        ('C10', _('C10: Reflection Guidance')),
        ('C11', _('C11: Care Team Affirmation')),
    ]

    # Primary Key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Relations
    option = models.ForeignKey(
        Option,
        on_delete=models.CASCADE,
        related_name='components'
    )

    # Component Info
    component_type = models.CharField(
        _('component type'),
        max_length=5,
        choices=COMPONENT_CHOICES
    )
    component_text = models.TextField(_('component text'))

    # Character count tracking
    character_count = models.IntegerField(
        _('character count'),
        null=True,
        blank=True
    )

    # Media
    image_url = models.TextField(
        _('image URL'),
        blank=True,
        default='',
        help_text=_('Cloudinary URL for component image/media')
    )
    media_type = models.CharField(
        _('media type'),
        max_length=20,
        blank=True,
        default='',
        choices=[
            ('image', _('Image')),
            ('video', _('Video')),
            ('audio', _('Audio')),
        ],
        help_text=_('Type of media attached to this component')
    )

    # Timestamps
    created_at = models.DateTimeField(_('created at'), default=timezone.now)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        db_table = 'components'
        verbose_name = _('component')
        verbose_name_plural = _('components')
        unique_together = [['option', 'component_type']]
        indexes = [
            models.Index(fields=['option'], name='idx_comp_option'),
            models.Index(fields=['component_type'], name='idx_comp_type'),
        ]

    def __str__(self):
        return f"{self.option.question.id} - Option {self.option.option_number} - {self.component_type}"

    def save(self, *args, **kwargs):
        """Auto-calculate character count on save."""
        if self.component_text:
            self.character_count = len(self.component_text)
        super().save(*args, **kwargs)


class PersonalPatternRecognition(models.Model):
    """PPR model - Synthesis texts for common selection patterns."""

    # Primary Key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Relations
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='ppr_patterns'
    )

    # Pattern Definition
    pattern_name = models.CharField(
        _('pattern name'),
        max_length=100,
        help_text=_('Descriptive pattern name')
    )

    # Selection Pattern (L1 + L2 + L3 option numbers)
    l1_option = models.IntegerField(_('L1 option number'))
    l2_options = ArrayField(
        models.IntegerField(),
        help_text=_('L2 option numbers (array for multi-select)')
    )
    l3_option = models.IntegerField(_('L3 option number'))

    # PPR Text
    ppr_text = models.TextField(
        _('PPR text'),
        help_text=_('440-550 characters, target 480')
    )

    # Metadata
    character_count = models.IntegerField(
        _('character count'),
        null=True,
        blank=True
    )
    coverage_percentage = models.DecimalField(
        _('coverage percentage'),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_('Estimated % of users this pattern covers')
    )

    # Timestamps
    created_at = models.DateTimeField(_('created at'), default=timezone.now)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        db_table = 'personal_pattern_recognition'
        verbose_name = _('personal pattern recognition')
        verbose_name_plural = _('personal pattern recognitions')
        indexes = [
            models.Index(fields=['question'], name='idx_ppr_question'),
        ]

    def __str__(self):
        return f"{self.question.id} - {self.pattern_name}"

    def save(self, *args, **kwargs):
        """Auto-calculate character count on save."""
        if self.ppr_text:
            self.character_count = len(self.ppr_text)
        super().save(*args, **kwargs)
