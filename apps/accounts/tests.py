"""
AWFM Accounts App - Test Cases

Comprehensive tests for user authentication, registration, and profile management.
"""

import pytest
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from unittest.mock import patch, MagicMock

User = get_user_model()


# ============================================================================
# Model Tests
# ============================================================================

@pytest.mark.django_db
class TestUserModel:
    """Test cases for the User model."""

    def test_create_user(self, create_user):
        """Test creating a regular user."""
        user = create_user(
            email='newuser@example.com',
            password='TestPass123!',
            display_name='New User'
        )
        assert user.email == 'newuser@example.com'
        assert user.display_name == 'New User'
        assert user.check_password('TestPass123!')
        assert not user.is_staff
        assert not user.is_superuser

    def test_create_user_without_email_raises_error(self):
        """Test that creating a user without email raises an error."""
        with pytest.raises(ValueError, match='Email'):
            User.objects.create_user(email='', password='test', display_name='Test')

    def test_create_superuser(self):
        """Test creating a superuser."""
        admin = User.objects.create_superuser(
            email='admin@example.com',
            password='AdminPass123!',
            display_name='Admin User'
        )
        assert admin.is_staff
        assert admin.is_superuser
        assert admin.email_verified

    def test_user_str_representation(self, user):
        """Test user string representation."""
        assert user.email in str(user)
        assert user.display_name in str(user)

    def test_get_full_name(self, create_user):
        """Test get_full_name method."""
        user = create_user(
            email='fullname@example.com',
            first_name='John',
            last_name='Doe'
        )
        assert user.get_full_name() == 'John Doe'

    def test_get_full_name_falls_back_to_display_name(self, create_user):
        """Test get_full_name falls back to display_name."""
        user = create_user(
            email='noname@example.com',
            display_name='Display Name'
        )
        assert user.get_full_name() == 'Display Name'

    def test_get_short_name(self, create_user):
        """Test get_short_name method."""
        user = create_user(
            email='shortname@example.com',
            first_name='Jane'
        )
        assert user.get_short_name() == 'Jane'

    def test_soft_delete(self, user):
        """Test soft delete functionality."""
        assert user.is_active
        assert user.deleted_at is None

        user.soft_delete()

        assert not user.is_active
        assert user.deleted_at is not None
        assert user.is_deleted

    def test_restore_deleted_user(self, user):
        """Test restoring a soft-deleted user."""
        user.soft_delete()
        user.restore()

        assert user.is_active
        assert user.deleted_at is None
        assert not user.is_deleted

    def test_attest_as_hcw(self, user):
        """Test HCW attestation."""
        assert not user.is_hcw
        assert user.hcw_attested_at is None

        user.attest_as_hcw()

        assert user.is_hcw
        assert user.hcw_attested_at is not None

    def test_verify_email(self, create_user):
        """Test email verification."""
        user = create_user(email_verified=False)
        user.email_verification_token = '123456'
        user.save()

        user.verify_email()

        assert user.email_verified
        assert user.email_verification_token == ''

    def test_can_be_permanently_deleted(self, user):
        """Test permanent deletion eligibility."""
        assert not user.can_be_permanently_deleted

        user.soft_delete()
        assert not user.can_be_permanently_deleted  # Still within 30 days

        # Simulate 31 days ago
        user.deleted_at = timezone.now() - timedelta(days=31)
        user.save()
        assert user.can_be_permanently_deleted


# ============================================================================
# Registration API Tests
# ============================================================================

@pytest.mark.django_db
class TestRegistrationAPI:
    """Test cases for user registration endpoint."""

    def test_register_user_success(self, api_client):
        """Test successful user registration."""
        with patch('apps.accounts.views.send_email_verification_code'):
            response = api_client.post('/api/v1/auth/register/', {
                'email': 'newuser@example.com',
                'password': 'SecurePass123!',
                'password2': 'SecurePass123!',
                'display_name': 'New User'
            })

        assert response.status_code == status.HTTP_201_CREATED
        assert 'user' in response.data
        assert 'tokens' in response.data
        assert response.data['user']['email'] == 'newuser@example.com'

    def test_register_user_password_mismatch(self, api_client):
        """Test registration fails with password mismatch."""
        response = api_client.post('/api/v1/auth/register/', {
            'email': 'test@example.com',
            'password': 'SecurePass123!',
            'password2': 'DifferentPass123!',
            'display_name': 'Test User'
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_user_duplicate_email(self, api_client, user):
        """Test registration fails with duplicate email."""
        response = api_client.post('/api/v1/auth/register/', {
            'email': user.email,
            'password': 'SecurePass123!',
            'password2': 'SecurePass123!',
            'display_name': 'Duplicate User'
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_user_weak_password(self, api_client):
        """Test registration fails with weak password."""
        response = api_client.post('/api/v1/auth/register/', {
            'email': 'test@example.com',
            'password': '123',
            'password2': '123',
            'display_name': 'Test User'
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_with_hcw_attestation(self, api_client):
        """Test registration with HCW attestation."""
        with patch('apps.accounts.views.send_email_verification_code'):
            response = api_client.post('/api/v1/auth/register/', {
                'email': 'hcw@example.com',
                'password': 'SecurePass123!',
                'password2': 'SecurePass123!',
                'display_name': 'HCW User',
                'is_hcw': True
            })

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['user']['is_hcw'] is True


# ============================================================================
# Login API Tests
# ============================================================================

@pytest.mark.django_db
class TestLoginAPI:
    """Test cases for login endpoint."""

    def test_login_success(self, api_client, user):
        """Test successful login."""
        response = api_client.post('/api/v1/auth/login/', {
            'email': user.email,
            'password': 'SecurePass123!'
        })

        assert response.status_code == status.HTTP_200_OK
        assert 'tokens' in response.data
        assert 'user' in response.data
        assert 'access' in response.data['tokens']
        assert 'refresh' in response.data['tokens']

    def test_login_wrong_password(self, api_client, user):
        """Test login fails with wrong password."""
        response = api_client.post('/api/v1/auth/login/', {
            'email': user.email,
            'password': 'WrongPassword123!'
        })

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_nonexistent_user(self, api_client):
        """Test login fails with nonexistent email."""
        response = api_client.post('/api/v1/auth/login/', {
            'email': 'nonexistent@example.com',
            'password': 'SomePassword123!'
        })

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_inactive_user(self, api_client, create_user):
        """Test login fails for inactive user."""
        user = create_user(is_active=False)

        response = api_client.post('/api/v1/auth/login/', {
            'email': user.email,
            'password': 'SecurePass123!'
        })

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ============================================================================
# Email Verification Tests
# ============================================================================

@pytest.mark.django_db
class TestEmailVerificationAPI:
    """Test cases for email verification."""

    def test_verify_email_success(self, api_client, create_user):
        """Test successful email verification."""
        user = create_user(email_verified=False)
        user.email_verification_token = '123456'
        user.email_verification_sent_at = timezone.now()
        user.save()

        response = api_client.post('/api/v1/auth/verify-email/', {
            'code': '123456'
        })

        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.email_verified

    def test_verify_email_invalid_code(self, api_client):
        """Test verification fails with invalid code."""
        response = api_client.post('/api/v1/auth/verify-email/', {
            'code': '000000'
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_verify_email_expired_code(self, api_client, create_user):
        """Test verification fails with expired code."""
        user = create_user(email_verified=False)
        user.email_verification_token = '123456'
        user.email_verification_sent_at = timezone.now() - timedelta(minutes=15)
        user.save()

        response = api_client.post('/api/v1/auth/verify-email/', {
            'code': '123456'
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'expired' in response.data['error'].lower()

    def test_resend_verification_code(self, authenticated_client, create_user):
        """Test resending verification code."""
        user = create_user(email_verified=False)

        # Re-authenticate as the unverified user
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)
        authenticated_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        with patch('apps.accounts.views.send_email_verification_code'):
            response = authenticated_client.post('/api/v1/auth/resend-verification/')

        assert response.status_code == status.HTTP_200_OK


# ============================================================================
# Profile API Tests
# ============================================================================

@pytest.mark.django_db
class TestProfileAPI:
    """Test cases for profile endpoints."""

    def test_get_profile(self, authenticated_client, user):
        """Test getting user profile."""
        response = authenticated_client.get('/api/v1/auth/profile/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == user.email
        assert response.data['display_name'] == user.display_name

    def test_get_profile_unauthenticated(self, api_client):
        """Test profile access requires authentication."""
        response = api_client.get('/api/v1/auth/profile/')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_profile(self, authenticated_client, user):
        """Test updating user profile."""
        response = authenticated_client.patch('/api/v1/auth/profile/', {
            'display_name': 'Updated Name',
            'bio': 'This is my bio',
            'pronouns': 'they/them'
        })

        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.display_name == 'Updated Name'
        assert user.bio == 'This is my bio'
        assert user.pronouns == 'they/them'

    def test_cannot_update_readonly_fields(self, authenticated_client, user):
        """Test that readonly fields cannot be updated."""
        original_email = user.email

        response = authenticated_client.patch('/api/v1/auth/profile/', {
            'email': 'newemail@example.com'
        })

        user.refresh_from_db()
        assert user.email == original_email  # Email should not change


# ============================================================================
# Password Change Tests
# ============================================================================

@pytest.mark.django_db
class TestPasswordChangeAPI:
    """Test cases for password change endpoint."""

    def test_request_password_change_code(self, authenticated_client):
        """Test requesting password change verification code."""
        with patch('apps.accounts.views.send_password_change_code'):
            response = authenticated_client.post('/api/v1/auth/request-password-change-code/')

        assert response.status_code == status.HTTP_200_OK

    def test_change_password_success(self, authenticated_client, user):
        """Test successful password change."""
        # Set up verification code
        user.password_change_code = '123456'
        user.password_change_code_expires_at = timezone.now() + timedelta(minutes=15)
        user.save()

        response = authenticated_client.post('/api/v1/auth/change-password/', {
            'verification_code': '123456',
            'old_password': 'SecurePass123!',
            'new_password': 'NewSecurePass456!',
            'new_password2': 'NewSecurePass456!'
        })

        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.check_password('NewSecurePass456!')

    def test_change_password_wrong_old_password(self, authenticated_client, user):
        """Test password change fails with wrong old password."""
        user.password_change_code = '123456'
        user.password_change_code_expires_at = timezone.now() + timedelta(minutes=15)
        user.save()

        response = authenticated_client.post('/api/v1/auth/change-password/', {
            'verification_code': '123456',
            'old_password': 'WrongPassword123!',
            'new_password': 'NewSecurePass456!',
            'new_password2': 'NewSecurePass456!'
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_change_password_invalid_verification_code(self, authenticated_client, user):
        """Test password change fails with invalid verification code."""
        response = authenticated_client.post('/api/v1/auth/change-password/', {
            'verification_code': '000000',
            'old_password': 'SecurePass123!',
            'new_password': 'NewSecurePass456!',
            'new_password2': 'NewSecurePass456!'
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ============================================================================
# Password Reset Tests
# ============================================================================

@pytest.mark.django_db
class TestPasswordResetAPI:
    """Test cases for password reset flow."""

    def test_forgot_password_existing_user(self, api_client, user):
        """Test forgot password for existing user."""
        with patch('apps.accounts.views.send_password_reset'):
            response = api_client.post('/api/v1/auth/forgot-password/', {
                'email': user.email
            })

        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.password_reset_token != ''

    def test_forgot_password_nonexistent_user(self, api_client):
        """Test forgot password for nonexistent user (should not reveal)."""
        response = api_client.post('/api/v1/auth/forgot-password/', {
            'email': 'nonexistent@example.com'
        })

        # Should still return 200 to not reveal if user exists
        assert response.status_code == status.HTTP_200_OK

    def test_reset_password_success(self, api_client, user):
        """Test successful password reset."""
        user.password_reset_token = 'valid-token'
        user.password_reset_expires_at = timezone.now() + timedelta(hours=1)
        user.save()

        response = api_client.post('/api/v1/auth/reset-password/', {
            'token': 'valid-token',
            'new_password': 'NewSecurePass456!',
            'new_password2': 'NewSecurePass456!'
        })

        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.check_password('NewSecurePass456!')
        assert user.password_reset_token == ''

    def test_reset_password_invalid_token(self, api_client):
        """Test password reset with invalid token."""
        response = api_client.post('/api/v1/auth/reset-password/', {
            'token': 'invalid-token',
            'new_password': 'NewSecurePass456!',
            'new_password2': 'NewSecurePass456!'
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_reset_password_expired_token(self, api_client, user):
        """Test password reset with expired token."""
        user.password_reset_token = 'expired-token'
        user.password_reset_expires_at = timezone.now() - timedelta(hours=1)
        user.save()

        response = api_client.post('/api/v1/auth/reset-password/', {
            'token': 'expired-token',
            'new_password': 'NewSecurePass456!',
            'new_password2': 'NewSecurePass456!'
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ============================================================================
# HCW Attestation Tests
# ============================================================================

@pytest.mark.django_db
class TestHCWAttestationAPI:
    """Test cases for HCW attestation endpoint."""

    def test_attest_hcw_success(self, authenticated_client, user):
        """Test successful HCW attestation."""
        response = authenticated_client.post('/api/v1/auth/attest-hcw/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['is_hcw'] is True
        assert response.data['hcw_attested_at'] is not None

        user.refresh_from_db()
        assert user.is_hcw

    def test_attest_hcw_unauthenticated(self, api_client):
        """Test HCW attestation requires authentication."""
        response = api_client.post('/api/v1/auth/attest-hcw/')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ============================================================================
# Account Deletion/Restoration Tests
# ============================================================================

@pytest.mark.django_db
class TestAccountDeletionAPI:
    """Test cases for account deletion and restoration."""

    def test_delete_account_success(self, authenticated_client, user):
        """Test successful account deletion."""
        with patch('apps.accounts.views.send_account_deletion_notification'):
            response = authenticated_client.post('/api/v1/auth/delete-account/', {
                'password': 'SecurePass123!'
            })

        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.is_deleted
        assert not user.is_active

    def test_delete_account_wrong_password(self, authenticated_client):
        """Test account deletion fails with wrong password."""
        response = authenticated_client.post('/api/v1/auth/delete-account/', {
            'password': 'WrongPassword123!'
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_request_account_restoration(self, api_client, create_user):
        """Test requesting account restoration code."""
        user = create_user()
        user.soft_delete()

        with patch('apps.accounts.views.send_account_restoration_code'):
            response = api_client.post('/api/v1/auth/request-restore/', {
                'email': user.email
            })

        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.restoration_code != ''

    def test_restore_account_success(self, api_client, create_user):
        """Test successful account restoration."""
        user = create_user()
        user.soft_delete()
        user.restoration_code = '123456'
        user.restoration_code_expires_at = timezone.now() + timedelta(hours=1)
        user.save()

        response = api_client.post('/api/v1/auth/restore-account/', {
            'email': user.email,
            'code': '123456'
        })

        assert response.status_code == status.HTTP_200_OK
        assert 'tokens' in response.data
        user.refresh_from_db()
        assert user.is_active
        assert not user.is_deleted


# ============================================================================
# Logout Tests
# ============================================================================

@pytest.mark.django_db
class TestLogoutAPI:
    """Test cases for logout endpoint."""

    def test_logout_success(self, authenticated_client):
        """Test successful logout."""
        response = authenticated_client.post('/api/v1/auth/logout/', {
            'refresh': 'some-refresh-token'
        })

        assert response.status_code == status.HTTP_200_OK

    def test_logout_unauthenticated(self, api_client):
        """Test logout requires authentication."""
        response = api_client.post('/api/v1/auth/logout/')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
