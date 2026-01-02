"""
AWFM Teams App - Serializers

Serializers for team management and memberships.
"""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Team, TeamMembership

User = get_user_model()


class TeamMemberSerializer(serializers.ModelSerializer):
    """Serializer for displaying team member info."""
    display_name = serializers.CharField(source='user.display_name', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    profile_photo_url = serializers.CharField(source='user.profile_photo_url', read_only=True)
    user_id = serializers.UUIDField(source='user.id', read_only=True)

    class Meta:
        model = TeamMembership
        fields = (
            'id',
            'user_id',
            'display_name',
            'email',
            'profile_photo_url',
            'role',
            'status',
            'is_default_guardian',
            'is_default_emergency_contact',
            'joined_at',
            'created_at',
        )
        read_only_fields = fields


class TeamSerializer(serializers.ModelSerializer):
    """Serializer for team display."""
    created_by_name = serializers.CharField(source='created_by.display_name', read_only=True)
    member_count = serializers.SerializerMethodField()
    members = TeamMemberSerializer(source='memberships', many=True, read_only=True)
    my_role = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = (
            'id',
            'name',
            'description',
            'avatar_url',
            'created_by',
            'created_by_name',
            'team_level',
            'member_count',
            'members',
            'my_role',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'created_by',
            'created_by_name',
            'member_count',
            'members',
            'my_role',
            'created_at',
            'updated_at',
        )

    def get_member_count(self, obj):
        """Get count of active members."""
        return obj.memberships.filter(status='active').count()

    def get_my_role(self, obj):
        """Get the current user's role in this team."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            membership = obj.memberships.filter(user=request.user, status='active').first()
            if membership:
                return membership.role
        return None


class CreateTeamSerializer(serializers.ModelSerializer):
    """Serializer for creating a new team."""

    class Meta:
        model = Team
        fields = ('name', 'description', 'avatar_url', 'team_level')
        extra_kwargs = {
            'name': {'required': True},
            'description': {'required': False},
            'avatar_url': {'required': False},
            'team_level': {'required': False},
        }

    def create(self, validated_data):
        """Create team and add creator as leader."""
        user = self.context['request'].user
        team = Team.objects.create(created_by=user, **validated_data)

        # Add creator as leader with active status
        TeamMembership.objects.create(
            team=team,
            user=user,
            role=TeamMembership.ROLE_LEADER,
            status=TeamMembership.STATUS_ACTIVE,
            is_default_guardian=True,
            is_default_emergency_contact=True,
        )

        return team


class InviteMemberSerializer(serializers.Serializer):
    """Serializer for inviting a member to a team."""
    email = serializers.EmailField(required=True)
    role = serializers.ChoiceField(
        choices=[
            (TeamMembership.ROLE_MEMBER, 'Member'),
            (TeamMembership.ROLE_WITNESS, 'Witness'),
        ],
        default=TeamMembership.ROLE_MEMBER
    )

    def validate_email(self, value):
        """Validate the email."""
        team = self.context['team']

        # Check if user exists
        try:
            user = User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("No user found with this email address.")

        # Check if already a member
        if team.memberships.filter(user=user).exclude(status='left').exists():
            raise serializers.ValidationError("This user is already a member or has a pending invitation.")

        return value


class AcceptInvitationSerializer(serializers.Serializer):
    """Serializer for accepting a team invitation."""
    token = serializers.CharField(required=True)

    def validate_token(self, value):
        """Validate the invitation token."""
        try:
            membership = TeamMembership.objects.get(
                invitation_token=value,
                status=TeamMembership.STATUS_PENDING
            )
        except TeamMembership.DoesNotExist:
            raise serializers.ValidationError("Invalid or expired invitation token.")

        # Check if expired
        from django.utils import timezone
        if membership.invitation_expires_at and timezone.now() > membership.invitation_expires_at:
            raise serializers.ValidationError("This invitation has expired.")

        return value


class UpdateMembershipSerializer(serializers.ModelSerializer):
    """Serializer for updating membership details."""

    class Meta:
        model = TeamMembership
        fields = (
            'role',
            'is_default_guardian',
            'is_default_emergency_contact',
        )

    def validate_role(self, value):
        """Validate role change."""
        instance = self.instance
        if instance and instance.role == TeamMembership.ROLE_LEADER and value != TeamMembership.ROLE_LEADER:
            # Check if there's another leader
            other_leaders = instance.team.memberships.filter(
                role=TeamMembership.ROLE_LEADER,
                status=TeamMembership.STATUS_ACTIVE
            ).exclude(id=instance.id).count()

            if other_leaders == 0:
                raise serializers.ValidationError(
                    "Cannot remove leader role. Assign another leader first."
                )
        return value
