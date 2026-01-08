"""
AWFM Accounts App - User Models

This module contains the custom User model with:
- Email-based authentication (no username)
- HCW attestation field (Pre-MVP)
- Google OAuth support
- Email verification
- Password reset tokens
- Profile fields (name, photo, bio, pronouns)
"""

import uuid
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.core.validators import EmailValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """Custom manager for User model with email-based authentication."""

    def create_user(self, email, password=None, **extra_fields):
        """Create and return a regular user with an email and password."""
        if not email:
            raise ValueError(_('The Email field must be set'))

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and return a superuser with an email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('email_verified', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model for AWFM platform.

    Uses email instead of username for authentication.
    Includes HCW attestation, OAuth support, and profile fields.
    """

    # Primary Key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text=_('Unique identifier for the user')
    )

    # Authentication
    email = models.EmailField(
        _('email address'),
        unique=True,
        max_length=255,
        validators=[EmailValidator()],
        help_text=_('User email address (used for login)')
    )
    # password field inherited from AbstractBaseUser

    # OAuth
    google_id = models.CharField(
        _('Google ID'),
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        help_text=_('Google OAuth identifier for social login')
    )

    # Profile
    display_name = models.CharField(
        _('display name'),
        max_length=255,
        help_text=_('Name shown to other users')
    )
    first_name = models.CharField(
        _('first name'),
        max_length=100,
        blank=True,
        default=''
    )
    last_name = models.CharField(
        _('last name'),
        max_length=100,
        blank=True,
        default=''
    )
    profile_photo_url = models.TextField(
        _('profile photo URL'),
        blank=True,
        default='',
        help_text=_('Cloudinary URL for profile photo (Batch 2)')
    )
    bio = models.TextField(
        _('bio'),
        blank=True,
        default='',
        help_text=_('User biography (Batch 5)')
    )
    pronouns = models.CharField(
        _('pronouns'),
        max_length=100,
        blank=True,
        default='',
        help_text=_('User pronouns (Batch 5)')
    )
    phone_number = models.CharField(
        _('phone number'),
        max_length=20,
        blank=True,
        default='',
        help_text=_('User phone number (optional)')
    )
    birth_date = models.DateField(
        _('birth date'),
        null=True,
        blank=True,
        help_text=_('User date of birth (optional)')
    )
    location = models.CharField(
        _('location'),
        max_length=255,
        blank=True,
        default='',
        help_text=_('User location/city (optional)')
    )

    # HCW Attestation (NEW in Pre-MVP)
    is_hcw = models.BooleanField(
        _('is healthcare worker'),
        default=False,
        help_text=_('User attestation that they are a healthcare worker (data collection only)')
    )
    hcw_attested_at = models.DateTimeField(
        _('HCW attestation timestamp'),
        null=True,
        blank=True,
        help_text=_('When the user attested to being an HCW')
    )

    # Email Verification
    email_verified = models.BooleanField(
        _('email verified'),
        default=False,
        help_text=_('Whether the user has verified their email address')
    )
    email_verification_token = models.CharField(
        _('email verification token'),
        max_length=255,
        blank=True,
        default='',
        help_text=_('Token sent in verification email')
    )
    email_verification_sent_at = models.DateTimeField(
        _('email verification sent at'),
        null=True,
        blank=True,
        help_text=_('When the verification email was sent')
    )

    # Password Reset
    password_reset_token = models.CharField(
        _('password reset token'),
        max_length=255,
        blank=True,
        default='',
        help_text=_('Token for password reset flow')
    )
    password_reset_expires_at = models.DateTimeField(
        _('password reset expires at'),
        null=True,
        blank=True,
        help_text=_('When the password reset token expires')
    )

    # Password Change Verification
    password_change_code = models.CharField(
        _('password change verification code'),
        max_length=6,
        blank=True,
        default='',
        help_text=_('6-digit verification code for password change')
    )
    password_change_code_expires_at = models.DateTimeField(
        _('password change code expires at'),
        null=True,
        blank=True,
        help_text=_('When the password change verification code expires (15 minutes)')
    )

    # Account Restoration (for soft-deleted accounts)
    restoration_code = models.CharField(
        _('account restoration code'),
        max_length=6,
        blank=True,
        default='',
        help_text=_('6-digit verification code for account restoration')
    )
    restoration_code_expires_at = models.DateTimeField(
        _('restoration code expires at'),
        null=True,
        blank=True,
        help_text=_('When the restoration verification code expires (1 hour)')
    )

    # Permissions
    is_staff = models.BooleanField(
        _('staff status'),
        default=False,
        help_text=_('Designates whether the user can log into the admin site.')
    )
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_('Designates whether this user should be treated as active.')
    )

    # Timestamps
    created_at = models.DateTimeField(
        _('created at'),
        default=timezone.now,
        help_text=_('When the user account was created')
    )
    updated_at = models.DateTimeField(
        _('updated at'),
        auto_now=True,
        help_text=_('When the user account was last updated')
    )
    last_login_at = models.DateTimeField(
        _('last login at'),
        null=True,
        blank=True,
        help_text=_('When the user last logged in')
    )

    # Soft Delete (GDPR compliance)
    deleted_at = models.DateTimeField(
        _('deleted at'),
        null=True,
        blank=True,
        help_text=_('When the user account was soft deleted (30-day retention)')
    )

    # Manager
    objects = UserManager()

    # Authentication settings
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['display_name']

    class Meta:
        db_table = 'users'
        verbose_name = _('user')
        verbose_name_plural = _('users')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email'], name='idx_users_email'),
            models.Index(fields=['google_id'], name='idx_users_google_id'),
            models.Index(fields=['deleted_at'], name='idx_users_deleted_at'),
        ]

    def __str__(self):
        """String representation of the user."""
        return f"{self.display_name} ({self.email})"

    def get_full_name(self):
        """Return the first_name plus the last_name, with a space in between."""
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name or self.display_name

    @property
    def full_name(self):
        """Property alias for get_full_name() for serializer compatibility."""
        return self.get_full_name()

    @property
    def avatar_url(self):
        """Property alias for profile_photo_url for serializer compatibility."""
        return self.profile_photo_url

    def get_short_name(self):
        """Return the short name for the user."""
        return self.first_name or self.display_name

    def soft_delete(self):
        """Soft delete the user account (GDPR compliance)."""
        self.deleted_at = timezone.now()
        self.is_active = False
        self.save(update_fields=['deleted_at', 'is_active', 'updated_at'])

    def restore(self):
        """Restore a soft-deleted user account."""
        self.deleted_at = None
        self.is_active = True
        self.save(update_fields=['deleted_at', 'is_active', 'updated_at'])

    def attest_as_hcw(self):
        """Mark the user as having attested to being an HCW."""
        self.is_hcw = True
        self.hcw_attested_at = timezone.now()
        self.save(update_fields=['is_hcw', 'hcw_attested_at', 'updated_at'])

    def verify_email(self):
        """Mark the user's email as verified."""
        self.email_verified = True
        self.email_verification_token = ''
        self.save(update_fields=['email_verified', 'email_verification_token', 'updated_at'])

    @property
    def is_deleted(self):
        """Check if the user is soft deleted."""
        return self.deleted_at is not None

    @property
    def can_be_permanently_deleted(self):
        """
        Check if the user can be permanently deleted.
        Users can be permanently deleted 30 days after soft deletion (GDPR).
        """
        if not self.deleted_at:
            return False

        from datetime import timedelta
        deletion_date = self.deleted_at + timedelta(days=30)
        return timezone.now() >= deletion_date
