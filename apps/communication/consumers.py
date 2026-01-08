"""
WebSocket consumers for real-time notifications.

AWFM uses WebSockets for:
- Real-time badge updates ("3 new")
- Live activity feed
- Instant notification bell updates
- Toast notifications
"""

import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer for user notifications.

    Each user joins their own notification group (user_{user_id}).
    Team notifications are sent to team groups (team_{team_id}).
    """

    async def connect(self):
        """Handle WebSocket connection."""
        self.user = self.scope.get('user')

        # Reject anonymous users
        if not self.user or self.user.is_anonymous:
            await self.close()
            return

        # Join user's personal notification group
        self.user_group = f'user_{self.user.id}'
        await self.channel_layer.group_add(
            self.user_group,
            self.channel_name
        )

        # Join all team groups the user belongs to
        self.team_groups = []
        team_ids = await self.get_user_team_ids()
        for team_id in team_ids:
            team_group = f'team_{team_id}'
            self.team_groups.append(team_group)
            await self.channel_layer.group_add(
                team_group,
                self.channel_name
            )

        await self.accept()

        # Send initial connection success message
        await self.send_json({
            'type': 'connection_established',
            'message': 'Connected to notification service',
            'user_group': self.user_group,
            'team_groups': self.team_groups,
        })

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        # Leave user group
        if hasattr(self, 'user_group'):
            await self.channel_layer.group_discard(
                self.user_group,
                self.channel_name
            )

        # Leave all team groups
        if hasattr(self, 'team_groups'):
            for team_group in self.team_groups:
                await self.channel_layer.group_discard(
                    team_group,
                    self.channel_name
                )

    async def receive_json(self, content):
        """
        Handle incoming WebSocket messages.

        Supported message types:
        - ping: Keep-alive
        - mark_read: Mark notification as read
        """
        message_type = content.get('type')

        if message_type == 'ping':
            await self.send_json({'type': 'pong'})

        elif message_type == 'mark_read':
            notification_id = content.get('notification_id')
            if notification_id:
                await self.mark_notification_read(notification_id)
                await self.send_json({
                    'type': 'notification_marked_read',
                    'notification_id': notification_id,
                })

    # ----- Event handlers (called via channel_layer.group_send) -----

    async def notification_new(self, event):
        """
        Handle new notification event.

        Called when a new notification is created for this user.
        """
        await self.send_json({
            'type': 'notification',
            'notification': event['notification'],
        })

    async def notification_toast(self, event):
        """
        Handle toast notification event.

        For immediate, ephemeral notifications (e.g., "Message sent!").
        """
        await self.send_json({
            'type': 'toast',
            'message': event['message'],
            'level': event.get('level', 'info'),  # info, success, warning, error
        })

    async def notification_badge_update(self, event):
        """
        Handle badge count update event.

        Sent when unread count changes.
        """
        await self.send_json({
            'type': 'badge_update',
            'unread_count': event['unread_count'],
        })

    async def team_activity(self, event):
        """
        Handle team activity event.

        Sent when something happens in a team (new message, affirmation, etc.).
        """
        await self.send_json({
            'type': 'team_activity',
            'team_id': event['team_id'],
            'activity': event['activity'],
        })

    async def question_completed(self, event):
        """
        Handle question completed event.

        Sent when a team member completes a question.
        """
        await self.send_json({
            'type': 'question_completed',
            'team_id': event['team_id'],
            'user_id': event['user_id'],
            'user_name': event['user_name'],
            'question_id': event['question_id'],
        })

    async def affirmation_received(self, event):
        """
        Handle affirmation received event.

        Sent when someone affirms your choices.
        """
        await self.send_json({
            'type': 'affirmation_received',
            'team_id': event['team_id'],
            'from_user_id': event['from_user_id'],
            'from_user_name': event['from_user_name'],
            'question_id': event['question_id'],
        })

    async def chat_message(self, event):
        """
        Handle new chat message event.

        Sent when a new message is posted in a channel.
        """
        await self.send_json({
            'type': 'chat_message',
            'team_id': event['team_id'],
            'channel_id': event['channel_id'],
            'message': event['message'],
        })

    # ----- Database helpers -----

    @database_sync_to_async
    def get_user_team_ids(self):
        """Get list of team IDs the user belongs to."""
        from apps.teams.models import TeamMembership

        return list(
            TeamMembership.objects.filter(
                user=self.user
            ).values_list('team_id', flat=True)
        )

    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        """Mark a notification as read."""
        from .models import Notification

        try:
            notification = Notification.objects.get(
                id=notification_id,
                user=self.user
            )
            notification.mark_as_read()
            return True
        except Notification.DoesNotExist:
            return False


# ----- Utility functions for sending notifications -----

async def send_user_notification(channel_layer, user_id, notification_data):
    """
    Send a notification to a specific user.

    Usage:
        from apps.communication.consumers import send_user_notification
        from channels.layers import get_channel_layer

        channel_layer = get_channel_layer()
        await send_user_notification(channel_layer, user.id, {
            'id': notification.id,
            'title': 'New message',
            'body': 'Someone sent you a message',
        })
    """
    await channel_layer.group_send(
        f'user_{user_id}',
        {
            'type': 'notification.new',
            'notification': notification_data,
        }
    )


async def send_toast(channel_layer, user_id, message, level='info'):
    """
    Send a toast notification to a specific user.

    Usage:
        await send_toast(channel_layer, user.id, 'Message sent!', 'success')
    """
    await channel_layer.group_send(
        f'user_{user_id}',
        {
            'type': 'notification.toast',
            'message': message,
            'level': level,
        }
    )


async def send_badge_update(channel_layer, user_id, unread_count):
    """
    Send badge count update to a specific user.

    Usage:
        await send_badge_update(channel_layer, user.id, 5)
    """
    await channel_layer.group_send(
        f'user_{user_id}',
        {
            'type': 'notification.badge_update',
            'unread_count': unread_count,
        }
    )


async def send_team_activity(channel_layer, team_id, activity_data):
    """
    Send activity update to all members of a team.

    Usage:
        await send_team_activity(channel_layer, team.id, {
            'type': 'message',
            'user_name': 'John',
            'content': 'Posted a new message',
        })
    """
    await channel_layer.group_send(
        f'team_{team_id}',
        {
            'type': 'team.activity',
            'team_id': str(team_id),
            'activity': activity_data,
        }
    )
