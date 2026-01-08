import uuid
from django.db import models
from django.conf import settings


class Notification(models.Model):
    """
    Persisted notification model for real-time and historical notifications.
    """
    TYPE_TEAM_INVITATION = 'team_invitation'
    TYPE_INVITATION_ACCEPTED = 'invitation_accepted'
    TYPE_MEMBER_JOINED = 'member_joined'
    TYPE_MEMBER_LEFT = 'member_left'
    TYPE_ROLE_CHANGED = 'role_changed'
    TYPE_AFFIRMATION = 'affirmation'
    TYPE_QUESTION_COMPLETED = 'question_completed'
    TYPE_CHAT_MESSAGE = 'chat_message'
    TYPE_GENERAL = 'general'

    NOTIFICATION_TYPES = [
        (TYPE_TEAM_INVITATION, 'Team Invitation'),
        (TYPE_INVITATION_ACCEPTED, 'Invitation Accepted'),
        (TYPE_MEMBER_JOINED, 'Member Joined'),
        (TYPE_MEMBER_LEFT, 'Member Left'),
        (TYPE_ROLE_CHANGED, 'Role Changed'),
        (TYPE_AFFIRMATION, 'Affirmation Received'),
        (TYPE_QUESTION_COMPLETED, 'Question Completed'),
        (TYPE_CHAT_MESSAGE, 'Chat Message'),
        (TYPE_GENERAL, 'General'),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    notification_type = models.CharField(
        max_length=50,
        choices=NOTIFICATION_TYPES,
        default=TYPE_GENERAL
    )
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True, default='')
    metadata = models.JSONField(default=dict, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'read_at']),
        ]

    def __str__(self):
        return f"{self.notification_type}: {self.title} for {self.user}"

    @property
    def is_read(self):
        return self.read_at is not None

    def mark_as_read(self):
        if not self.read_at:
            from django.utils import timezone
            self.read_at = timezone.now()
            self.save(update_fields=['read_at'])
