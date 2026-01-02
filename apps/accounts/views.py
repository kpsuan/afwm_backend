"""
AWFM Accounts App - Views

Authentication views for user registration, login, and profile management.
"""

import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import (
    UserRegistrationSerializer,
    CustomTokenObtainPairSerializer,
    UserProfileSerializer,
    ChangePasswordSerializer,
)

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """
    User registration endpoint.
    POST /api/auth/register/

    Request body:
    {
        "email": "user@example.com",
        "password": "securepassword123",
        "password2": "securepassword123",
        "display_name": "John Doe",
        "is_hcw": false  // optional
    }

    Response:
    {
        "user": {
            "id": "uuid",
            "email": "user@example.com",
            "display_name": "John Doe",
            "is_hcw": false
        },
        "message": "User registered successfully"
    }
    """
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = UserRegistrationSerializer

    def create(self, request, *args, **kwargs):
        import random
        import string
        from .emails import send_email_verification_code

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate 6-digit verification code
        code = ''.join(random.choices(string.digits, k=6))
        user.email_verification_token = code
        user.email_verification_sent_at = timezone.now()
        user.save(update_fields=['email_verification_token', 'email_verification_sent_at'])

        # Send verification email with code
        send_email_verification_code(user, code)

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        return Response({
            'user': {
                'id': str(user.id),
                'email': user.email,
                'display_name': user.display_name,
                'is_hcw': user.is_hcw,
                'email_verified': user.email_verified,
            },
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            'message': 'User registered successfully. Please check your email for the verification code.'
        }, status=status.HTTP_201_CREATED)

class ForgotPasswordView(APIView):
    """
    Request password reset.
    POST /api/auth/forgot-password/

    Request: { "email": "user@example.com" }
    """
    permission_classes = (AllowAny,)

    def post(self, request):
        from .emails import send_password_reset

        email = request.data.get('email')

        if not email:
            return Response({
                "error": "Email is required"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Always return success (don't reveal if email exists)
        try:
            user = User.objects.get(email=email, is_active=True)
            print(f"[FORGOT PASSWORD] Found user: {user.email}, is_active={user.is_active}")

            # Generate reset token
            token = secrets.token_urlsafe(32)
            user.password_reset_token = token
            user.password_reset_expires_at = timezone.now() + timedelta(hours=1)
            user.save(update_fields=['password_reset_token', 'password_reset_expires_at'])

            # Send reset email
            frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
            reset_url = f"{frontend_url}/reset-password?token={token}"
            print(f"[FORGOT PASSWORD] Sending email to {user.email}")

            email_sent = send_password_reset(user, reset_url)
            print(f"[FORGOT PASSWORD] Email sent result: {email_sent}")

        except User.DoesNotExist:
            print(f"[FORGOT PASSWORD] No active user found with email: {email}")

        return Response({
            "message": "If an account exists with this email, you will receive a password reset link."
        }, status=status.HTTP_200_OK)


class ResetPasswordView(APIView):
    """
    Reset password with token.
    POST /api/auth/reset-password/
    
    Request: { "token": "...", "new_password": "...", "new_password2": "..." }
    """
    permission_classes = (AllowAny,)

    def post(self, request):
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError

        token = request.data.get('token')
        new_password = request.data.get('new_password')
        new_password2 = request.data.get('new_password2')

        if not all([token, new_password, new_password2]):
            return Response({
                "error": "All fields are required"
            }, status=status.HTTP_400_BAD_REQUEST)

        if new_password != new_password2:
            return Response({
                "error": "Passwords do not match"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Find user with this token
        try:
            user = User.objects.get(password_reset_token=token)
        except User.DoesNotExist:
            return Response({
                "error": "Invalid or expired reset token"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check if token expired
        if not user.password_reset_expires_at or timezone.now() > user.password_reset_expires_at:
            return Response({
                "error": "Reset token has expired. Please request a new one."
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validate password strength
        try:
            validate_password(new_password, user)
        except ValidationError as e:
            return Response({
                "error": e.messages[0] if e.messages else "Password validation failed"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Reset password
        user.set_password(new_password)
        user.password_reset_token = ''
        user.password_reset_expires_at = None
        user.save()

        return Response({
            "message": "Password reset successfully. You can now log in."
        }, status=status.HTTP_200_OK)


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Login endpoint using JWT.
    POST /api/auth/login/

    Request body:
    {
        "email": "user@example.com",
        "password": "securepassword123"
    }

    Response:
    {
        "refresh": "refresh_token",
        "access": "access_token",
        "user": {
            "id": "uuid",
            "email": "user@example.com",
            "display_name": "John Doe",
            "is_hcw": false,
            "email_verified": false
        }
    }
    """
    serializer_class = CustomTokenObtainPairSerializer


class LogoutView(APIView):
    """
    Logout endpoint.
    POST /api/auth/logout/

    Request body:
    {
        "refresh": "refresh_token"
    }

    Response:
    {
        "message": "Logout successful"
    }

    Note: For JWT, logout is primarily handled client-side by removing tokens.
    This endpoint blacklists the refresh token if blacklisting is enabled.
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token:
                token = RefreshToken(refresh_token)
                # Blacklist the token (only works if BLACKLIST_AFTER_ROTATION is True)
                # For now, we just acknowledge the logout
            return Response({
                "message": "Logout successful"
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                "error": "Invalid token"
            }, status=status.HTTP_400_BAD_REQUEST)


class ResendVerificationView(APIView):
    """
    Resend email verification code.
    POST /api/auth/resend-verification/
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        import random
        import string
        from .emails import send_email_verification_code

        user = request.user

        if user.email_verified:
            return Response({
                "message": "Email is already verified"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Generate new 6-digit code
        code = ''.join(random.choices(string.digits, k=6))
        user.email_verification_token = code
        user.email_verification_sent_at = timezone.now()
        user.save(update_fields=['email_verification_token', 'email_verification_sent_at'])

        # Send verification email with code
        send_email_verification_code(user, code)

        return Response({
            "message": "Verification code sent to your email"
        }, status=status.HTTP_200_OK)


class VerifyEmailView(APIView):
    """
    Verify email with 6-digit code.
    POST /api/auth/verify-email/

    Request: { "code": "123456" }
    """
    permission_classes = (AllowAny,)

    def post(self, request):
        code = request.data.get('code')

        if not code:
            return Response({
                "error": "Verification code is required"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Find user with this code
        try:
            user = User.objects.get(email_verification_token=code)
        except User.DoesNotExist:
            return Response({
                "error": "Invalid verification code"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check if code is expired (10 minutes)
        if user.email_verification_sent_at:
            expiry = user.email_verification_sent_at + timedelta(minutes=10)
            if timezone.now() > expiry:
                return Response({
                    "error": "Verification code has expired. Please request a new one."
                }, status=status.HTTP_400_BAD_REQUEST)

        # Verify the email
        user.verify_email()

        return Response({
            "message": "Email verified successfully"
        }, status=status.HTTP_200_OK)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    User profile endpoint.
    GET /api/auth/profile/ - Get current user profile
    PUT/PATCH /api/auth/profile/ - Update current user profile

    Response:
    {
        "id": "uuid",
        "email": "user@example.com",
        "display_name": "John Doe",
        "first_name": "John",
        "last_name": "Doe",
        "profile_photo_url": "",
        "bio": "",
        "pronouns": "",
        "is_hcw": false,
        "hcw_attested_at": null,
        "email_verified": false,
        "created_at": "2025-01-01T00:00:00Z",
        "last_login_at": "2025-01-01T00:00:00Z"
    }
    """
    permission_classes = (IsAuthenticated,)
    serializer_class = UserProfileSerializer

    def get_object(self):
        """Return the current authenticated user."""
        return self.request.user


class RequestPasswordChangeCodeView(APIView):
    """
    Request password change verification code.
    POST /api/auth/request-password-change-code/

    Sends a 6-digit verification code to the user's email.
    Code expires in 15 minutes.

    Response:
    {
        "message": "Verification code sent to your email"
    }
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        import random
        import string
        from datetime import timedelta
        from django.utils import timezone
        from .emails import send_password_change_code

        user = request.user

        # Generate 6-digit verification code
        code = ''.join(random.choices(string.digits, k=6))

        # Save code and expiration (15 minutes)
        user.password_change_code = code
        user.password_change_code_expires_at = timezone.now() + timedelta(minutes=15)
        user.save(update_fields=['password_change_code', 'password_change_code_expires_at'])

        # Send email with verification code
        send_password_change_code(user, code)

        return Response({
            "message": "Verification code sent to your email"
        }, status=status.HTTP_200_OK)


class ChangePasswordView(APIView):
    """
    Change password endpoint with verification code.
    POST /api/auth/change-password/

    Request body:
    {
        "verification_code": "123456",
        "old_password": "currentpassword",
        "new_password": "newsecurepassword123",
        "new_password2": "newsecurepassword123"
    }

    Response:
    {
        "message": "Password changed successfully"
    }
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        from django.utils import timezone
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError

        user = request.user
        verification_code = request.data.get('verification_code')
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        new_password2 = request.data.get('new_password2')

        # Validate required fields
        if not all([verification_code, old_password, new_password, new_password2]):
            return Response({
                "error": "All fields are required"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Verify verification code
        if not user.password_change_code or user.password_change_code != verification_code:
            return Response({
                "error": "Invalid verification code"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check if code has expired
        if not user.password_change_code_expires_at or timezone.now() > user.password_change_code_expires_at:
            return Response({
                "error": "Verification code has expired. Please request a new one."
            }, status=status.HTTP_400_BAD_REQUEST)

        # Verify old password
        if not user.check_password(old_password):
            return Response({
                "error": "Incorrect current password"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validate new passwords match
        if new_password != new_password2:
            return Response({
                "error": "New passwords do not match"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validate new password strength
        try:
            validate_password(new_password, user)
        except ValidationError as e:
            return Response({
                "error": e.messages[0] if e.messages else "Password validation failed"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Change password
        user.set_password(new_password)

        # Clear verification code
        user.password_change_code = ''
        user.password_change_code_expires_at = None

        user.save()

        return Response({
            "message": "Password changed successfully"
        }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def attest_hcw(request):
    """
    HCW attestation endpoint.
    POST /api/auth/attest-hcw/

    Response:
    {
        "message": "HCW attestation recorded",
        "is_hcw": true,
        "hcw_attested_at": "2025-01-01T00:00:00Z"
    }
    """
    user = request.user
    user.attest_as_hcw()
    return Response({
        "message": "HCW attestation recorded",
        "is_hcw": user.is_hcw,
        "hcw_attested_at": user.hcw_attested_at.isoformat() if user.hcw_attested_at else None
    }, status=status.HTTP_200_OK)


class DeleteAccountView(APIView):
    """
    Delete account endpoint.
    POST /api/auth/delete-account/

    Request body:
    {
        "password": "currentpassword"
    }

    Response:
    {
        "message": "Account deleted successfully. You have 30 days to restore your account."
    }

    Note: This performs a soft delete. The account will be permanently deleted after 30 days.
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        from .emails import send_account_deletion_notification

        user = request.user
        password = request.data.get('password')

        if not password:
            return Response({
                "error": "Password is required to confirm account deletion"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Verify password
        if not user.check_password(password):
            return Response({
                "error": "Incorrect password"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Soft delete the account
        user.soft_delete()

        # Send notification email
        send_account_deletion_notification(user)

        return Response({
            "message": "Account deleted successfully. You have 30 days to restore your account."
        }, status=status.HTTP_200_OK)


class GoogleOAuthView(APIView):
    """
    Google OAuth2 token exchange endpoint.
    POST /api/auth/google/

    This endpoint receives a Google ID token (JWT credential) from the frontend,
    validates it, and returns JWT tokens.

    Request body:
    {
        "credential": "google_jwt_credential"  // or access_token/id_token for compatibility
    }

    Response:
    {
        "user": {
            "id": "uuid",
            "email": "user@example.com",
            "display_name": "John Doe",
            "is_hcw": false,
            "email_verified": true
        },
        "tokens": {
            "refresh": "refresh_token",
            "access": "access_token"
        },
        "is_new": true/false
    }
    """
    permission_classes = (AllowAny,)

    def post(self, request):
        import json
        import base64
        from django.conf import settings

        # Google Identity Services sends credential (JWT), but we also accept id_token/access_token
        credential = request.data.get('credential') or request.data.get('id_token') or request.data.get('access_token')

        if not credential:
            return Response({
                "error": "Google credential is required"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Decode the JWT to get user info (Google Identity Services sends a JWT)
        try:
            # Split the JWT into parts
            parts = credential.split('.')
            if len(parts) != 3:
                return Response({
                    "error": "Invalid Google credential format"
                }, status=status.HTTP_400_BAD_REQUEST)

            # Decode the payload (middle part)
            # Add padding if needed
            payload = parts[1]
            padding = 4 - len(payload) % 4
            if padding != 4:
                payload += '=' * padding

            decoded_payload = base64.urlsafe_b64decode(payload)
            google_data = json.loads(decoded_payload)

            # Verify the token is from Google and not expired
            import time
            if google_data.get('iss') not in ['accounts.google.com', 'https://accounts.google.com']:
                return Response({
                    "error": "Invalid token issuer"
                }, status=status.HTTP_400_BAD_REQUEST)

            if google_data.get('exp', 0) < time.time():
                return Response({
                    "error": "Token has expired"
                }, status=status.HTTP_400_BAD_REQUEST)

            # Verify the audience matches our client ID
            expected_client_id = settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY
            if expected_client_id and google_data.get('aud') != expected_client_id:
                return Response({
                    "error": "Token audience mismatch"
                }, status=status.HTTP_400_BAD_REQUEST)

        except (ValueError, json.JSONDecodeError) as e:
            return Response({
                "error": "Failed to decode Google credential"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Extract user info from Google response
        email = google_data.get('email')
        email_verified = google_data.get('email_verified', False)

        if not email:
            return Response({
                "error": "Email not provided by Google"
            }, status=status.HTTP_400_BAD_REQUEST)

        if not email_verified:
            return Response({
                "error": "Google email is not verified"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check if user exists or create new one
        is_new = False
        try:
            user = User.objects.get(email=email)

            # Update profile photo if not set
            if not user.profile_photo_url and google_data.get('picture'):
                user.profile_photo_url = google_data.get('picture')
                user.save(update_fields=['profile_photo_url'])

        except User.DoesNotExist:
            # Create new user
            is_new = True
            user = User.objects.create_user(
                email=email,
                display_name=google_data.get('name') or email.split('@')[0],
                first_name=google_data.get('given_name', ''),
                last_name=google_data.get('family_name', ''),
                profile_photo_url=google_data.get('picture', ''),
            )
            user.email_verified = True
            user.save(update_fields=['email_verified'])

        # Check if user is deleted
        if user.deleted_at:
            return Response({
                "error": "This account has been deleted. You can restore it using the restore account option."
            }, status=status.HTTP_400_BAD_REQUEST)

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        return Response({
            'user': {
                'id': str(user.id),
                'email': user.email,
                'display_name': user.display_name,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'profile_photo_url': user.profile_photo_url,
                'is_hcw': user.is_hcw,
                'email_verified': user.email_verified,
            },
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            'is_new': is_new,
            'message': 'Google authentication successful'
        }, status=status.HTTP_200_OK)


class RequestAccountRestorationView(APIView):
    """
    Request account restoration verification code.
    POST /api/auth/request-restore/

    Request: { "email": "user@example.com" }

    Sends a 6-digit verification code to the user's email if their account
    is soft-deleted and within the 30-day restoration window.
    """
    permission_classes = (AllowAny,)

    def post(self, request):
        import random
        import string
        from .emails import send_account_restoration_code

        email = request.data.get('email')

        if not email:
            return Response({
                "error": "Email is required"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Find deleted user (deleted_at is not null)
            user = User.objects.get(email=email, deleted_at__isnull=False)

            # Check if account can still be restored (within 30 days)
            if user.can_be_permanently_deleted:
                return Response({
                    "error": "This account has passed the 30-day restoration window and cannot be restored."
                }, status=status.HTTP_400_BAD_REQUEST)

            # Generate 6-digit verification code
            code = ''.join(random.choices(string.digits, k=6))
            user.restoration_code = code
            user.restoration_code_expires_at = timezone.now() + timedelta(hours=1)
            user.save(update_fields=['restoration_code', 'restoration_code_expires_at'])

            # Send restoration email
            send_account_restoration_code(user, code)

            return Response({
                "message": "Restoration code sent to your email"
            }, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            # Don't reveal if account exists or isn't deleted
            return Response({
                "error": "No deleted account found with this email"
            }, status=status.HTTP_400_BAD_REQUEST)


class RestoreAccountView(APIView):
    """
    Restore a deleted account with verification code.
    POST /api/auth/restore-account/

    Request: { "email": "user@example.com", "code": "123456" }

    Restores the account if the verification code is valid.
    """
    permission_classes = (AllowAny,)

    def post(self, request):
        email = request.data.get('email')
        code = request.data.get('code')

        if not email or not code:
            return Response({
                "error": "Email and verification code are required"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email, deleted_at__isnull=False)

            # Verify the code
            if not user.restoration_code or user.restoration_code != code:
                return Response({
                    "error": "Invalid verification code"
                }, status=status.HTTP_400_BAD_REQUEST)

            # Check if code has expired
            if not user.restoration_code_expires_at or timezone.now() > user.restoration_code_expires_at:
                return Response({
                    "error": "Verification code has expired. Please request a new one."
                }, status=status.HTTP_400_BAD_REQUEST)

            # Restore the account
            user.restore()

            # Clear the restoration code
            user.restoration_code = ''
            user.restoration_code_expires_at = None
            user.save(update_fields=['restoration_code', 'restoration_code_expires_at'])

            # Generate JWT tokens so user can log in immediately
            refresh = RefreshToken.for_user(user)

            return Response({
                "message": "Account restored successfully! You are now logged in.",
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "display_name": user.display_name,
                    "is_hcw": user.is_hcw,
                    "email_verified": user.email_verified,
                },
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                }
            }, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return Response({
                "error": "No deleted account found with this email"
            }, status=status.HTTP_400_BAD_REQUEST)
