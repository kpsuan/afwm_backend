"""
Common Utility Functions

Shared helper functions used across multiple apps.
"""

import secrets
import string


def generate_token(length=32):
    """Generate a secure random token."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_invitation_token():
    """Generate a token for team invitations."""
    return generate_token(64)


def generate_verification_token():
    """Generate a token for email verification."""
    return generate_token(32)


def generate_password_reset_token():
    """Generate a token for password reset."""
    return generate_token(32)
