"""
Email utilities for team-related notifications.

Uses Django's email backend (configured for SendGrid in production).
"""

from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger('teams.emails')


def send_team_invitation(user, team, inviter, invitation_url):
    """
    Send team invitation email.

    Args:
        user: User being invited
        team: Team they're being invited to
        inviter: User who sent the invitation
        invitation_url: URL to accept the invitation

    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    subject = f"You're invited to join {team.name} on AWFM"

    message = f"""
Hello {user.display_name},

{inviter.display_name} has invited you to join their care team "{team.name}" on AWFM (A Whole Family Matter).

Click the link below to accept the invitation:

{invitation_url}

This invitation will expire in 7 days.

If you don't want to join this team, you can simply ignore this email.

Best regards,
The AWFM Team
    """.strip()

    html_message = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #667eea;">Team Invitation</h2>
                <p>Hello {user.display_name},</p>
                <p><strong>{inviter.display_name}</strong> has invited you to join their care team "<strong>{team.name}</strong>" on AWFM (A Whole Family Matter).</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{invitation_url}"
                       style="background-color: #667eea; color: white; padding: 14px 28px; text-decoration: none; border-radius: 6px; font-weight: bold;">
                        Accept Invitation
                    </a>
                </div>
                <p style="color: #718096; font-size: 14px;">This invitation will expire in <strong>7 days</strong>.</p>
                <p style="color: #718096; font-size: 14px;">
                    If you don't want to join this team, you can simply ignore this email.
                </p>
                <p style="margin-top: 30px;">
                    Best regards,<br>
                    The AWFM Team
                </p>
            </div>
        </body>
    </html>
    """.strip()

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Team invitation sent to {user.email} for team {team.name}")
        return True
    except Exception as e:
        logger.error(f"Failed to send team invitation to {user.email}: {e}")
        return False


def send_signup_invitation(email, team, inviter, signup_url, custom_message=''):
    """
    Send invitation email to someone who doesn't have an account yet.

    Args:
        email: Email address of the person being invited
        team: Team they're being invited to
        inviter: User who sent the invitation
        signup_url: URL to sign up and join the team
        custom_message: Optional custom message from the inviter

    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    subject = f"You're invited to join {team.name} on AWFM"

    # Include custom message if provided
    message_section = ""
    html_message_section = ""
    if custom_message:
        message_section = f'\n\nMessage from {inviter.display_name}:\n"{custom_message}"\n'
        html_message_section = f'''
            <div style="background: #f8f9fa; padding: 16px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #667eea;">
                <p style="margin: 0 0 8px 0; font-weight: bold; color: #333;">Message from {inviter.display_name}:</p>
                <p style="margin: 0; color: #555; font-style: italic;">"{custom_message}"</p>
            </div>
        '''

    message = f"""
Hello!

{inviter.display_name} has invited you to join their care team "{team.name}" on AWFM (A Whole Family Matter).
{message_section}
AWFM helps families plan for advance care decisions together. Create your free account to join the team:

{signup_url}

This invitation will expire in 7 days.

If you don't want to join this team, you can simply ignore this email.

Best regards,
The AWFM Team
    """.strip()

    html_message = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #667eea;">You're Invited!</h2>
                <p>Hello!</p>
                <p><strong>{inviter.display_name}</strong> has invited you to join their care team "<strong>{team.name}</strong>" on AWFM (A Whole Family Matter).</p>
                {html_message_section}
                <p>AWFM helps families plan for advance care decisions together. Create your free account to join the team:</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{signup_url}"
                       style="background-color: #667eea; color: white; padding: 14px 28px; text-decoration: none; border-radius: 6px; font-weight: bold;">
                        Sign Up & Join Team
                    </a>
                </div>
                <p style="color: #718096; font-size: 14px;">This invitation will expire in <strong>7 days</strong>.</p>
                <p style="color: #718096; font-size: 14px;">
                    If you don't want to join this team, you can simply ignore this email.
                </p>
                <p style="margin-top: 30px;">
                    Best regards,<br>
                    The AWFM Team
                </p>
            </div>
        </body>
    </html>
    """.strip()

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Signup invitation sent to {email} for team {team.name}")
        return True
    except Exception as e:
        logger.error(f"Failed to send signup invitation to {email}: {e}")
        return False


def send_invitation_accepted_notification(team_leader, new_member, team):
    """
    Notify team leader when someone accepts their invitation.

    Args:
        team_leader: Leader of the team
        new_member: User who accepted the invitation
        team: The team they joined

    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    subject = f"{new_member.display_name} joined your team on AWFM"

    message = f"""
Hello {team_leader.display_name},

Great news! {new_member.display_name} has accepted your invitation and joined your care team "{team.name}".

Log in to AWFM to see your updated team.

Best regards,
The AWFM Team
    """.strip()

    html_message = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #667eea;">New Team Member!</h2>
                <p>Hello {team_leader.display_name},</p>
                <p>Great news! <strong>{new_member.display_name}</strong> has accepted your invitation and joined your care team "<strong>{team.name}</strong>".</p>
                <p>Log in to AWFM to see your updated team.</p>
                <p style="margin-top: 30px;">
                    Best regards,<br>
                    The AWFM Team
                </p>
            </div>
        </body>
    </html>
    """.strip()

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[team_leader.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Invitation accepted notification sent to {team_leader.email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send invitation accepted notification: {e}")
        return False


def send_member_left_notification(team_leader, member, team):
    """
    Notify team leader when a member leaves the team.

    Args:
        team_leader: Leader of the team
        member: User who left
        team: The team they left

    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    subject = f"{member.display_name} left your team on AWFM"

    message = f"""
Hello {team_leader.display_name},

{member.display_name} has left your care team "{team.name}".

You may want to invite someone else to fill their role.

Best regards,
The AWFM Team
    """.strip()

    html_message = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #667eea;">Team Update</h2>
                <p>Hello {team_leader.display_name},</p>
                <p><strong>{member.display_name}</strong> has left your care team "<strong>{team.name}</strong>".</p>
                <p>You may want to invite someone else to fill their role.</p>
                <p style="margin-top: 30px;">
                    Best regards,<br>
                    The AWFM Team
                </p>
            </div>
        </body>
    </html>
    """.strip()

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[team_leader.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Member left notification sent to {team_leader.email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send member left notification: {e}")
        return False
