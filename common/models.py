"""
Common Abstract Base Models

These abstract models provide shared functionality across all apps.
Use these as base classes to ensure consistency.
"""

import uuid
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class BaseModel(models.Model):
    """
    Abstract base model with UUID primary key and timestamps.

    All models should inherit from this unless there's a specific reason not to.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text=_('Unique identifier')
    )

    created_at = models.DateTimeField(
        _('created at'),
        default=timezone.now,
        help_text=_('When this record was created')
    )

    updated_at = models.DateTimeField(
        _('updated at'),
        auto_now=True,
        help_text=_('When this record was last updated')
    )

    class Meta:
        abstract = True
        ordering = ['-created_at']


class SoftDeleteModel(BaseModel):
    """
    Abstract model with soft delete functionality.

    Use this for models where records should be hidden but not permanently deleted.
    Supports GDPR compliance with 30-day retention.
    """

    deleted_at = models.DateTimeField(
        _('deleted at'),
        null=True,
        blank=True,
        help_text=_('When this record was soft deleted')
    )

    class Meta:
        abstract = True

    @property
    def is_deleted(self):
        """Check if the record is soft deleted."""
        return self.deleted_at is not None

    def soft_delete(self):
        """Soft delete this record."""
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at', 'updated_at'])

    def restore(self):
        """Restore a soft-deleted record."""
        self.deleted_at = None
        self.save(update_fields=['deleted_at', 'updated_at'])

    @property
    def can_be_permanently_deleted(self):
        """
        Check if the record can be permanently deleted.
        Records can be permanently deleted 30 days after soft deletion (GDPR).
        """
        if not self.deleted_at:
            return False

        from datetime import timedelta
        deletion_date = self.deleted_at + timedelta(days=30)
        return timezone.now() >= deletion_date
