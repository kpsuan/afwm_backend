"""
AWFM Accounts App - Serializers

Serializers for user authentication and profile management.
Includes registration, login, and user profile serializers.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    Handles email, password, display_name, and optional HCW attestation.
    """
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password2 = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        label='Confirm Password'
    )

    class Meta:
        model = User
        fields = ('email', 'password', 'password2', 'display_name', 'is_hcw')
        extra_kwargs = {
            'email': {'required': True},
            'display_name': {'required': True},
            'is_hcw': {'required': False, 'default': False}
        }

    def validate(self, attrs):
        """Validate that passwords match."""
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({
                "password": "Password fields didn't match."
            })
        return attrs

    def create(self, validated_data):
        """Create a new user with the validated data."""
        # Remove password2 as it's not needed for user creation
        validated_data.pop('password2')

        # Extract is_hcw before creating user
        is_hcw = validated_data.pop('is_hcw', False)

        # Create user
        user = User.objects.create_user(**validated_data)

        # Attest as HCW if specified
        if is_hcw:
            user.attest_as_hcw()

        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT token serializer that adds user data to the response.
    Returns tokens wrapped in a 'tokens' object to match frontend expectations.
    """
    def validate(self, attrs):
        data = super().validate(attrs)

        # Extract tokens and wrap them in a 'tokens' object
        # to match the format expected by the frontend
        access = data.pop('access')
        refresh = data.pop('refresh')

        data['tokens'] = {
            'access': access,
            'refresh': refresh,
        }

        # Add user data to the response
        data['user'] = {
            'id': str(self.user.id),
            'email': self.user.email,
            'display_name': self.user.display_name,
            'is_hcw': self.user.is_hcw,
            'email_verified': self.user.email_verified,
        }

        return data


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile display and updates.
    Excludes sensitive fields like password and tokens.
    """
    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'display_name',
            'first_name',
            'last_name',
            'profile_photo_url',
            'bio',
            'pronouns',
            'is_hcw',
            'hcw_attested_at',
            'email_verified',
            'created_at',
            'last_login_at',
        )
        read_only_fields = (
            'id',
            'email',
            'hcw_attested_at',
            'email_verified',
            'created_at',
            'last_login_at',
        )


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change endpoint."""
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        validators=[validate_password]
    )
    new_password2 = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        """Validate that new passwords match."""
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({
                "new_password": "Password fields didn't match."
            })
        return attrs

    def validate_old_password(self, value):
        """Validate that the old password is correct."""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value

    def save(self):
        """Update the user's password."""
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user
