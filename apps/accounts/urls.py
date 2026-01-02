"""
AWFM Accounts App - URL Configuration

Authentication endpoints for registration, login, logout, and profile management.
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

app_name = 'accounts'

urlpatterns = [
    # Registration
    path('register/', views.RegisterView.as_view(), name='register'),

    path('verify-email/', views.VerifyEmailView.as_view(), name='verify_email'),
    path('resend-verification/', views.ResendVerificationView.as_view(), name='resend_verification'),

    # Login/Logout
    path('login/', views.CustomTokenObtainPairView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),

    # Google OAuth
    path('google/', views.GoogleOAuthView.as_view(), name='google_oauth'),

    path('forgot-password/', views.ForgotPasswordView.as_view(), name='forgot_password'),
    path('reset-password/', views.ResetPasswordView.as_view(), name='reset_password'),

    # Token refresh
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # User profile
    path('profile/', views.UserProfileView.as_view(), name='profile'),

    # Password management
    path('request-password-change-code/', views.RequestPasswordChangeCodeView.as_view(), name='request_password_change_code'),
    path('change-password/', views.ChangePasswordView.as_view(), name='change_password'),

    # Account deletion
    path('delete-account/', views.DeleteAccountView.as_view(), name='delete_account'),

    # Account restoration
    path('request-restore/', views.RequestAccountRestorationView.as_view(), name='request_restore'),
    path('restore-account/', views.RestoreAccountView.as_view(), name='restore_account'),

    # HCW attestation
    path('attest-hcw/', views.attest_hcw, name='attest_hcw'),
]
