"""
Notification utility functions for creating and sending notifications.

This module provides synchronous functions for creating notifications
and sending real-time WebSocket updates.
"""

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import Notification


def create_notification(user, notification_type, title, body='', metadata=None):
    """
    Create a notification and send it via WebSocket.

    Args:
        user: The user to notify
        notification_type: Type from Notification.NOTIFICATION_TYPES
        title: Notification title
        body: Optional notification body
        metadata: Optional dict with extra data (team_id, invitation_token, etc.)

    Returns:
        The created Notification instance
    """
    notification = Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        body=body,
        metadata=metadata or {}
    )

    # Send WebSocket notification
    send_realtime_notification(user.id, notification)

    return notification


def send_realtime_notification(user_id, notification):
    """
    Send a notification to a user via WebSocket.

    Args:
        user_id: The user's ID (UUID)
        notification: The Notification instance
    """
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    notification_data = {
        'id': str(notification.id),
        'notification_type': notification.notification_type,
        'title': notification.title,
        'body': notification.body,
        'metadata': notification.metadata,
        'is_read': notification.is_read,
        'created_at': notification.created_at.isoformat(),
    }

    async_to_sync(channel_layer.group_send)(
        f'user_{user_id}',
        {
            'type': 'notification.new',
            'notification': notification_data,
        }
    )


def send_toast_notification(user_id, message, level='info'):
    """
    Send a toast notification to a user via WebSocket.

    Args:
        user_id: The user's ID (UUID)
        message: Toast message
        level: 'info', 'success', 'warning', or 'error'
    """
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    async_to_sync(channel_layer.group_send)(
        f'user_{user_id}',
        {
            'type': 'notification.toast',
            'message': message,
            'level': level,
        }
    )


def send_badge_update(user_id):
    """
    Send updated unread count to a user via WebSocket.

    Args:
        user_id: The user's ID (UUID)
    """
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    unread_count = Notification.objects.filter(
        user_id=user_id,
        read_at__isnull=True
    ).count()

    async_to_sync(channel_layer.group_send)(
        f'user_{user_id}',
        {
            'type': 'notification.badge_update',
            'unread_count': unread_count,
        }
    )


# ----- Convenience functions for common notification types -----

def notify_team_invitation(invited_user, team, invited_by, invitation_token=None):
    """
    Send notification when a user is invited to a team.

    Args:
        invited_user: The user being invited
        team: The team they're being invited to
        invited_by: The user who sent the invitation
        invitation_token: The token to accept/decline the invitation
    """
    return create_notification(
        user=invited_user,
        notification_type=Notification.TYPE_TEAM_INVITATION,
        title=f'You\'ve been invited to join {team.name}',
        body=f'{invited_by.display_name} has invited you to join their care team.',
        metadata={
            'team_id': str(team.id),
            'team_name': team.name,
            'invited_by_id': str(invited_by.id),
            'invited_by_name': invited_by.display_name,
            'invitation_token': invitation_token,
        }
    )


def notify_invitation_accepted(team_leader, new_member, team):
    """
    Send notification when someone accepts a team invitation.

    Args:
        team_leader: The team leader to notify
        new_member: The user who accepted
        team: The team they joined
    """
    return create_notification(
        user=team_leader,
        notification_type=Notification.TYPE_INVITATION_ACCEPTED,
        title=f'{new_member.display_name} joined {team.name}',
        body=f'{new_member.display_name} has accepted your invitation and is now a member of your care team.',
        metadata={
            'team_id': str(team.id),
            'team_name': team.name,
            'new_member_id': str(new_member.id),
            'new_member_name': new_member.display_name,
        }
    )


def notify_member_left(team_leader, member, team):
    """
    Send notification when someone leaves a team.

    Args:
        team_leader: The team leader to notify
        member: The user who left
        team: The team they left
    """
    return create_notification(
        user=team_leader,
        notification_type=Notification.TYPE_MEMBER_LEFT,
        title=f'{member.display_name} left {team.name}',
        body=f'{member.display_name} has left your care team.',
        metadata={
            'team_id': str(team.id),
            'team_name': team.name,
            'member_id': str(member.id),
            'member_name': member.display_name,
        }
    )


def notify_member_joined(team_leader, new_member, team):
    """
    Send notification when a new member joins (for pending invitations converted).

    Args:
        team_leader: The team leader to notify
        new_member: The user who joined
        team: The team they joined
    """
    return create_notification(
        user=team_leader,
        notification_type=Notification.TYPE_MEMBER_JOINED,
        title=f'{new_member.display_name} joined {team.name}',
        body=f'{new_member.display_name} has signed up and joined your care team.',
        metadata={
            'team_id': str(team.id),
            'team_name': team.name,
            'new_member_id': str(new_member.id),
            'new_member_name': new_member.display_name,
        }
    )


def notify_affirmation(recording_owner, affirming_user, recording):
    """
    Send notification when someone affirms a recording.

    Args:
        recording_owner: The user who owns the recording
        affirming_user: The user who affirmed
        recording: The recording that was affirmed
    """
    # Send persistent notification
    notification = create_notification(
        user=recording_owner,
        notification_type=Notification.TYPE_AFFIRMATION,
        title=f'{affirming_user.display_name} affirmed your choices',
        body=f'{affirming_user.display_name} affirmed your recording for "{recording.question.title}".',
        metadata={
            'recording_id': str(recording.id),
            'question_id': recording.question_id,
            'question_title': recording.question.title,
            'affirming_user_id': str(affirming_user.id),
            'affirming_user_name': affirming_user.display_name,
            'team_id': str(recording.team_id) if recording.team_id else None,
        }
    )

    # Also send a toast for immediate feedback
    send_toast_notification(
        recording_owner.id,
        f'{affirming_user.display_name} affirmed your choices!',
        level='success'
    )

    return notification
