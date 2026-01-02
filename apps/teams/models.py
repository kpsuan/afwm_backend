"""
AWFM Teams App - Team Models

This module contains models for care teams and memberships:
- Team model
- TeamMembership model with witness role and leader defaults
"""

import uuid
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Team(models.Model):
    """
    Care team model.

    A team consists of 3-6 people planning together for advance care decisions.
    """

    # Primary Key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text=_('Unique identifier for the team')
    )

    # Team Info
    name = models.CharField(
        _('team name'),
        max_length=255,
        help_text=_('Name of the care team')
    )
    description = models.TextField(
        _('description'),
        blank=True,
        default='',
        help_text=_('Team description (Batch 8)')
    )
    avatar_url = models.TextField(
        _('avatar URL'),
        blank=True,
        default='',
        help_text=_('Cloudinary URL for team avatar (Batch 4)')
    )

    # Leader
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,  # Prevent deletion of team creator
        related_name='teams_created',
        help_text=_('User who created this team (team leader)')
    )

    # Team Level (MVP - multi-team support)
    team_level = models.IntegerField(
        _('team level'),
        null=True,
        blank=True,
        choices=[
            (1, _('Level 1: Immediate Family')),
            (2, _('Level 2: Family Back Home')),
            (3, _('Level 3: Local Chosen Family'))
        ],
        help_text=_('Team level for multi-team support (MVP, not Pre-MVP)')
    )

    # Timestamps
    created_at = models.DateTimeField(
        _('created at'),
        default=timezone.now,
        help_text=_('When the team was created')
    )
    updated_at = models.DateTimeField(
        _('updated at'),
        auto_now=True,
        help_text=_('When the team was last updated')
    )

    # Soft Delete
    deleted_at = models.DateTimeField(
        _('deleted at'),
        null=True,
        blank=True,
        help_text=_('When the team was soft deleted (Batch 9+10)')
    )

    class Meta:
        db_table = 'teams'
        verbose_name = _('team')
        verbose_name_plural = _('teams')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_by'], name='idx_teams_created_by'),
            models.Index(fields=['deleted_at'], name='idx_teams_deleted_at'),
        ]

    def __str__(self):
        """String representation of the team."""
        return self.name

    @property
    def is_deleted(self):
        """Check if the team is soft deleted."""
        return self.deleted_at is not None

    def soft_delete(self):
        """Soft delete the team."""
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at', 'updated_at'])

    def restore(self):
        """Restore a soft-deleted team."""
        self.deleted_at = None
        self.save(update_fields=['deleted_at', 'updated_at'])

    def get_active_members(self):
        """Get all active members of this team."""
        return self.memberships.filter(status='active')

    def get_leader(self):
        """Get the team leader."""
        return self.memberships.filter(role='leader', status='active').first()


class TeamMembership(models.Model):
    """
    Team membership model with roles, witness support, and leader defaults.

    Roles:
    - leader: Creates team, invites members, default guardian/emergency contact
    - member: Regular team member
    - witness: Distinct role - can have agents but cannot BE agent for team members
    """

    # Role choices
    ROLE_LEADER = 'leader'
    ROLE_MEMBER = 'member'
    ROLE_WITNESS = 'witness'

    ROLE_CHOICES = [
        (ROLE_LEADER, _('Leader')),
        (ROLE_MEMBER, _('Member')),
        (ROLE_WITNESS, _('Witness')),
    ]

    # Status choices
    STATUS_PENDING = 'pending'
    STATUS_ACTIVE = 'active'
    STATUS_LEFT = 'left'

    STATUS_CHOICES = [
        (STATUS_PENDING, _('Pending')),
        (STATUS_ACTIVE, _('Active')),
        (STATUS_LEFT, _('Left')),
    ]

    # Primary Key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text=_('Unique identifier for the membership')
    )

    # Relations
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='memberships',
        help_text=_('The team this membership belongs to')
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='team_memberships',
        help_text=_('The user who is a member of this team')
    )

    # Role
    role = models.CharField(
        _('role'),
        max_length=20,
        choices=ROLE_CHOICES,
        help_text=_('Role within the team (leader/member/witness)')
    )

    # Leader Defaults (NEW in Pre-MVP)
    # Automatically set to TRUE for all members when leader creates team
    is_default_guardian = models.BooleanField(
        _('is default guardian'),
        default=False,
        help_text=_('Leader is default guardian for this member')
    )
    is_default_emergency_contact = models.BooleanField(
        _('is default emergency contact'),
        default=False,
        help_text=_('Leader is default emergency contact for this member')
    )

    # Member Overrides (NEW in Pre-MVP)
    # Members can override leader defaults with their own designations
    guardian_override = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='guardian_for_memberships',
        help_text=_('Member-specified guardian (overrides leader default)')
    )
    emergency_contact_override = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='emergency_contact_for_memberships',
        help_text=_('Member-specified emergency contact (overrides leader default)')
    )

    # Invitation
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invitations_sent',
        help_text=_('User who invited this member')
    )
    invitation_token = models.CharField(
        _('invitation token'),
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        help_text=_('Unique token for invitation link')
    )
    invitation_sent_at = models.DateTimeField(
        _('invitation sent at'),
        null=True,
        blank=True,
        help_text=_('When the invitation was sent')
    )
    invitation_expires_at = models.DateTimeField(
        _('invitation expires at'),
        null=True,
        blank=True,
        help_text=_('When the invitation expires')
    )

    # Status
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        help_text=_('Membership status')
    )
    joined_at = models.DateTimeField(
        _('joined at'),
        null=True,
        blank=True,
        help_text=_('When the user accepted the invitation')
    )
    left_at = models.DateTimeField(
        _('left at'),
        null=True,
        blank=True,
        help_text=_('When the user left the team')
    )

    # Timestamps
    created_at = models.DateTimeField(
        _('created at'),
        default=timezone.now,
        help_text=_('When the membership was created')
    )
    updated_at = models.DateTimeField(
        _('updated at'),
        auto_now=True,
        help_text=_('When the membership was last updated')
    )

    class Meta:
        db_table = 'team_memberships'
        verbose_name = _('team membership')
        verbose_name_plural = _('team memberships')
        ordering = ['created_at']
        unique_together = [['team', 'user']]
        indexes = [
            models.Index(fields=['team'], name='idx_tm_team'),
            models.Index(fields=['user'], name='idx_tm_user'),
            models.Index(fields=['invitation_token'], name='idx_tm_invite_token'),
            models.Index(fields=['status'], name='idx_tm_status'),
        ]
        constraints = [
            # Witness cannot be guardian or emergency contact for team members
            models.CheckConstraint(
                condition=(
                    ~models.Q(role='witness') |
                    (
                        models.Q(guardian_override__isnull=True) &
                        models.Q(guardian_override__isnull=True)
                    )
                ),
                name='witness_cannot_be_agent',
                violation_error_message=_('Witness cannot be designated as guardian or emergency contact')
            ),
        ]

    def __str__(self):
        """String representation of the membership."""
        return f"{self.user.display_name} - {self.get_role_display()} in {self.team.name}"

    def clean(self):
        """Validate the membership."""
        super().clean()

        # Witness cannot be guardian or emergency contact
        if self.role == self.ROLE_WITNESS:
            if self.guardian_override or self.emergency_contact_override:
                raise ValidationError({
                    'role': _('Witness cannot be designated as guardian or emergency contact for team members')
                })

    def save(self, *args, **kwargs):
        """Save the membership with validation."""
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_leader(self):
        """Check if this is a leader membership."""
        return self.role == self.ROLE_LEADER

    @property
    def is_witness(self):
        """Check if this is a witness membership."""
        return self.role == self.ROLE_WITNESS

    @property
    def is_active(self):
        """Check if the membership is active."""
        return self.status == self.STATUS_ACTIVE

    @property
    def is_pending(self):
        """Check if the membership is pending."""
        return self.status == self.STATUS_PENDING

    def get_guardian(self):
        """
        Get the guardian for this member.
        Returns override if set, otherwise returns leader if default is enabled.
        """
        if self.guardian_override:
            return self.guardian_override
        elif self.is_default_guardian:
            leader_membership = self.team.get_leader()
            return leader_membership.user if leader_membership else None
        return None

    def get_emergency_contact(self):
        """
        Get the emergency contact for this member.
        Returns override if set, otherwise returns leader if default is enabled.
        """
        if self.emergency_contact_override:
            return self.emergency_contact_override
        elif self.is_default_emergency_contact:
            leader_membership = self.team.get_leader()
            return leader_membership.user if leader_membership else None
        return None

    def accept_invitation(self):
        """Accept the invitation and activate the membership."""
        self.status = self.STATUS_ACTIVE
        self.joined_at = timezone.now()
        self.invitation_token = None  # Clear the token
        self.save(update_fields=['status', 'joined_at', 'invitation_token', 'updated_at'])

    def leave_team(self):
        """Leave the team."""
        self.status = self.STATUS_LEFT
        self.left_at = timezone.now()
        self.save(update_fields=['status', 'left_at', 'updated_at'])
