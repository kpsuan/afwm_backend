"""
Email utilities for account-related notifications.

Uses Django's email backend (configured for SendGrid in production).
"""

from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
import logging

logger = logging.getLogger('accounts.emails')


def send_account_deletion_notification(user):
    """
    Send email notification when user deletes their account.

    Args:
        user: User instance being deleted

    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    subject = 'Your AWFM Account Has Been Deleted'

    # Plain text message
    message = f"""
Hello {user.display_name},

Your AWFM (A Whole Family Matter) account has been successfully deleted.

If you didn't request this deletion, please contact our support team immediately at support@awfm.com.

Your account will be permanently deleted after 30 days. If you wish to restore your account within this period, please contact support.

Thank you for using AWFM.

Best regards,
The AWFM Team
    """.strip()

    # HTML message (optional)
    html_message = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #667eea;">Account Deletion Confirmation</h2>
                <p>Hello {user.display_name},</p>
                <p>Your AWFM (A Whole Family Matter) account has been successfully deleted.</p>
                <p style="background-color: #fff5f5; border-left: 4px solid #e53e3e; padding: 12px; margin: 20px 0;">
                    <strong>Important:</strong> If you didn't request this deletion, please contact our support team immediately at
                    <a href="mailto:support@awfm.com">support@awfm.com</a>.
                </p>
                <p>Your account will be permanently deleted after <strong>30 days</strong>. If you wish to restore your account within this period, please contact support.</p>
                <p>Thank you for using AWFM.</p>
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
        logger.info(f"Account deletion notification sent to {user.email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send account deletion notification to {user.email}: {e}")
        return False


def send_password_change_code(user, verification_code):
    """
    Send verification code for password change.

    Args:
        user: User instance requesting password change
        verification_code: 6-digit verification code

    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    subject = 'Your AWFM Password Change Verification Code'

    # Plain text message
    message = f"""
Hello {user.display_name},

You requested to change your password for your AWFM account.

Your verification code is: {verification_code}

This code will expire in 15 minutes.

If you didn't request this password change, please ignore this email or contact support at support@awfm.com.

Best regards,
The AWFM Team
    """.strip()

    # HTML message
    html_message = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #667eea;">Password Change Verification</h2>
                <p>Hello {user.display_name},</p>
                <p>You requested to change your password for your AWFM account.</p>
                <div style="background-color: #f7fafc; border-radius: 8px; padding: 20px; margin: 20px 0; text-align: center;">
                    <p style="margin: 0 0 10px 0; font-size: 14px; color: #718096;">Your verification code is:</p>
                    <p style="margin: 0; font-size: 32px; font-weight: bold; color: #667eea; letter-spacing: 8px; font-family: 'Courier New', monospace;">
                        {verification_code}
                    </p>
                </div>
                <p style="color: #718096; font-size: 14px;">This code will expire in <strong>15 minutes</strong>.</p>
                <p style="background-color: #fff5f5; border-left: 4px solid #e53e3e; padding: 12px; margin: 20px 0; font-size: 14px;">
                    If you didn't request this password change, please ignore this email or contact support at
                    <a href="mailto:support@awfm.com">support@awfm.com</a>.
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
        logger.info(f"Password change verification code sent to {user.email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send password change code to {user.email}: {e}")
        return False

def send_email_verification_code(user, verification_code):
    """
    Send 6-digit verification code to new user.

    Args:
        user: User instance
        verification_code: 6-digit verification code

    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    subject = 'Verify Your AWFM Email Address'

    message = f"""
Hello {user.display_name},

Welcome to AWFM (A Whole Family Matter)!

Your email verification code is: {verification_code}

This code will expire in 10 minutes.

If you didn't create an account, please ignore this email.

Best regards,
The AWFM Team
    """.strip()

    html_message = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #667eea;">Verify Your Email</h2>
                <p>Hello {user.display_name},</p>
                <p>Welcome to AWFM (A Whole Family Matter)!</p>
                <div style="background-color: #f7fafc; border-radius: 8px; padding: 20px; margin: 20px 0; text-align: center;">
                    <p style="margin: 0 0 10px 0; font-size: 14px; color: #718096;">Your verification code is:</p>
                    <p style="margin: 0; font-size: 32px; font-weight: bold; color: #667eea; letter-spacing: 8px; font-family: 'Courier New', monospace;">
                        {verification_code}
                    </p>
                </div>
                <p style="color: #718096; font-size: 14px;">This code will expire in <strong>10 minutes</strong>.</p>
                <p style="background-color: #fff5f5; border-left: 4px solid #e53e3e; padding: 12px; margin: 20px 0; font-size: 14px;">
                    If you didn't create an account, please ignore this email.
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
        logger.info(f"Email verification code sent to {user.email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send verification email to {user.email}: {e}")
        return False

def send_password_reset(user, reset_url):
    """
    Send password reset link.

    Args:
        user: User instance
        reset_url: Full URL with token for password reset
    """
    subject = 'Reset Your AWFM Password'

    message = f"""
Hello {user.display_name},

You requested to reset your password for your AWFM account.

Click the link below to reset your password:

{reset_url}

This link will expire in 1 hour.

If you didn't request this, please ignore this email. Your password will remain unchanged.

Best regards,
The AWFM Team
    """.strip()

    html_message = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #667eea;">Password Reset Request</h2>
                <p>Hello {user.display_name},</p>
                <p>You requested to reset your password for your AWFM account.</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}" 
                       style="background-color: #667eea; color: white; padding: 14px 28px; text-decoration: none; border-radius: 6px; font-weight: bold;">
                        Reset Password
                    </a>
                </div>
                <p style="color: #718096; font-size: 14px;">This link will expire in <strong>1 hour</strong>.</p>
                <p style="background-color: #fff5f5; border-left: 4px solid #e53e3e; padding: 12px; margin: 20px 0; font-size: 14px;">
                    If you didn't request this, please ignore this email. Your password will remain unchanged.
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
        logger.info(f"Password reset email sent to {user.email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send password reset email to {user.email}: {e}")
        return False


def send_account_restoration_code(user, verification_code):
    """
    Send verification code for account restoration.

    Args:
        user: User instance requesting account restoration
        verification_code: 6-digit verification code

    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    subject = 'Restore Your AWFM Account'

    # Plain text message
    message = f"""
Hello {user.display_name},

You requested to restore your AWFM account.

Your verification code is: {verification_code}

This code will expire in 1 hour.

If you didn't request this, please ignore this email. Your account will remain deleted.

Best regards,
The AWFM Team
    """.strip()

    # HTML message
    html_message = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #667eea;">Restore Your Account</h2>
                <p>Hello {user.display_name},</p>
                <p>You requested to restore your AWFM account.</p>
                <div style="background-color: #f7fafc; border-radius: 8px; padding: 20px; margin: 20px 0; text-align: center;">
                    <p style="margin: 0 0 10px 0; font-size: 14px; color: #718096;">Your verification code is:</p>
                    <p style="margin: 0; font-size: 32px; font-weight: bold; color: #667eea; letter-spacing: 8px; font-family: 'Courier New', monospace;">
                        {verification_code}
                    </p>
                </div>
                <p style="color: #718096; font-size: 14px;">This code will expire in <strong>1 hour</strong>.</p>
                <p style="background-color: #e6fffa; border-left: 4px solid #38b2ac; padding: 12px; margin: 20px 0; font-size: 14px;">
                    Once restored, your account and all your data will be fully accessible again.
                </p>
                <p style="background-color: #fff5f5; border-left: 4px solid #e53e3e; padding: 12px; margin: 20px 0; font-size: 14px;">
                    If you didn't request this, please ignore this email. Your account will remain deleted.
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
        logger.info(f"Account restoration code sent to {user.email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send account restoration code to {user.email}: {e}")
        return False
