"""
Social Auth Pipeline for AWFM

Custom pipeline functions for handling Google OAuth user creation
and profile updates.
"""

from django.contrib.auth import get_user_model

User = get_user_model()


def create_user(strategy, details, backend, user=None, *args, **kwargs):
    """
    Create a user account for social auth if one doesn't exist.

    This replaces the default create_user pipeline to work with
    our custom User model that uses email as the username.
    """
    if user:
        return {'is_new': False}

    # Get email from social auth details
    email = details.get('email')
    if not email:
        return None

    # Check if user already exists
    try:
        existing_user = User.objects.get(email=email)
        return {'is_new': False, 'user': existing_user}
    except User.DoesNotExist:
        pass

    # Create new user
    fields = {
        'email': email,
        'display_name': details.get('fullname') or details.get('first_name') or email.split('@')[0],
        'first_name': details.get('first_name', ''),
        'last_name': details.get('last_name', ''),
        'email_verified': True,  # Google already verified the email
    }

    # Create user without password (social auth only)
    new_user = User.objects.create_user(**fields)

    return {
        'is_new': True,
        'user': new_user,
    }


def save_profile(backend, user, response, *args, **kwargs):
    """
    Save additional profile data from the OAuth provider.

    Updates profile photo URL and other fields from Google profile.
    """
    if backend.name == 'google-oauth2':
        # Get profile photo from Google
        picture = response.get('picture')
        if picture and not user.profile_photo_url:
            user.profile_photo_url = picture

        # Update first/last name if not set
        if not user.first_name and response.get('given_name'):
            user.first_name = response.get('given_name')

        if not user.last_name and response.get('family_name'):
            user.last_name = response.get('family_name')

        # Ensure email is verified for Google OAuth users
        if not user.email_verified:
            user.email_verified = True

        user.save()
