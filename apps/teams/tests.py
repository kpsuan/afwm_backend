"""
AWFM Teams App - Test Cases

Comprehensive tests for team management, memberships, and invitations.
"""

import pytest
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework import status
from unittest.mock import patch

from apps.teams.models import Team, TeamMembership

User = get_user_model()


# ============================================================================
# Model Tests
# ============================================================================

@pytest.mark.django_db
class TestTeamModel:
    """Test cases for the Team model."""

    def test_create_team(self, user):
        """Test creating a team."""
        team = Team.objects.create(
            name='Test Team',
            description='A test care team',
            created_by=user
        )
        assert team.name == 'Test Team'
        assert team.created_by == user
        assert team.deleted_at is None
        assert not team.is_deleted

    def test_team_str_representation(self, team):
        """Test team string representation."""
        assert str(team) == team.name

    def test_soft_delete_team(self, team):
        """Test soft delete functionality."""
        assert not team.is_deleted
        team.soft_delete()
        assert team.is_deleted
        assert team.deleted_at is not None

    def test_restore_team(self, team):
        """Test restoring a soft-deleted team."""
        team.soft_delete()
        team.restore()
        assert not team.is_deleted
        assert team.deleted_at is None

    def test_get_active_members(self, team, create_user):
        """Test getting active members."""
        # Team already has leader as active member from fixture
        member_user = create_user(email='member@example.com')
        TeamMembership.objects.create(
            team=team,
            user=member_user,
            role=TeamMembership.ROLE_MEMBER,
            status=TeamMembership.STATUS_ACTIVE
        )

        active_members = team.get_active_members()
        assert active_members.count() == 2

    def test_get_leader(self, team, user):
        """Test getting team leader."""
        leader = team.get_leader()
        assert leader is not None
        assert leader.user == user
        assert leader.role == TeamMembership.ROLE_LEADER


@pytest.mark.django_db
class TestTeamMembershipModel:
    """Test cases for the TeamMembership model."""

    def test_create_membership(self, team, create_user):
        """Test creating a team membership."""
        member_user = create_user(email='member@example.com')
        membership = TeamMembership.objects.create(
            team=team,
            user=member_user,
            role=TeamMembership.ROLE_MEMBER,
            status=TeamMembership.STATUS_ACTIVE
        )

        assert membership.team == team
        assert membership.user == member_user
        assert membership.is_active

    def test_membership_str_representation(self, team, user):
        """Test membership string representation."""
        membership = team.memberships.get(user=user)
        assert user.display_name in str(membership)
        assert team.name in str(membership)

    def test_membership_is_leader_property(self, team, user):
        """Test is_leader property."""
        membership = team.memberships.get(user=user)
        assert membership.is_leader

    def test_membership_is_witness_property(self, team, create_user):
        """Test is_witness property."""
        witness_user = create_user(email='witness@example.com')
        witness = TeamMembership.objects.create(
            team=team,
            user=witness_user,
            role=TeamMembership.ROLE_WITNESS,
            status=TeamMembership.STATUS_ACTIVE
        )
        assert witness.is_witness

    def test_accept_invitation(self, team, create_user):
        """Test accepting an invitation."""
        invited_user = create_user(email='invited@example.com')
        membership = TeamMembership.objects.create(
            team=team,
            user=invited_user,
            role=TeamMembership.ROLE_MEMBER,
            status=TeamMembership.STATUS_PENDING,
            invitation_token='test-token'
        )

        assert membership.is_pending
        membership.accept_invitation()

        assert membership.is_active
        assert membership.joined_at is not None
        assert membership.invitation_token is None

    def test_leave_team(self, team, create_user):
        """Test leaving a team."""
        member_user = create_user(email='member@example.com')
        membership = TeamMembership.objects.create(
            team=team,
            user=member_user,
            role=TeamMembership.ROLE_MEMBER,
            status=TeamMembership.STATUS_ACTIVE
        )

        membership.leave_team()

        assert membership.status == TeamMembership.STATUS_LEFT
        assert membership.left_at is not None

    def test_get_guardian_with_override(self, team, create_user, user):
        """Test getting guardian with override."""
        member_user = create_user(email='member@example.com')
        guardian_user = create_user(email='guardian@example.com')

        membership = TeamMembership.objects.create(
            team=team,
            user=member_user,
            role=TeamMembership.ROLE_MEMBER,
            status=TeamMembership.STATUS_ACTIVE,
            guardian_override=guardian_user
        )

        assert membership.get_guardian() == guardian_user

    def test_get_guardian_default_leader(self, team, create_user, user):
        """Test getting guardian defaults to leader."""
        member_user = create_user(email='member@example.com')
        membership = TeamMembership.objects.create(
            team=team,
            user=member_user,
            role=TeamMembership.ROLE_MEMBER,
            status=TeamMembership.STATUS_ACTIVE,
            is_default_guardian=True
        )

        assert membership.get_guardian() == user  # Leader


# ============================================================================
# Team List/Create API Tests
# ============================================================================

@pytest.mark.django_db
class TestTeamListCreateAPI:
    """Test cases for team list and create endpoints."""

    def test_list_teams(self, authenticated_client, team):
        """Test listing user's teams."""
        response = authenticated_client.get('/api/v1/teams/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1

    def test_list_teams_unauthenticated(self, api_client):
        """Test teams list requires authentication."""
        response = api_client.get('/api/v1/teams/')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_team(self, authenticated_client):
        """Test creating a new team."""
        response = authenticated_client.post('/api/v1/teams/', {
            'name': 'New Care Team',
            'description': 'A new team for testing'
        })

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['team']['name'] == 'New Care Team'

    def test_create_team_without_name(self, authenticated_client):
        """Test team creation requires name."""
        response = authenticated_client.post('/api/v1/teams/', {
            'description': 'Missing name'
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ============================================================================
# Team Detail API Tests
# ============================================================================

@pytest.mark.django_db
class TestTeamDetailAPI:
    """Test cases for team detail endpoints."""

    def test_get_team_detail(self, authenticated_client, team):
        """Test getting team details."""
        response = authenticated_client.get(f'/api/v1/teams/{team.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == str(team.id)
        assert response.data['name'] == team.name

    def test_get_nonexistent_team(self, authenticated_client):
        """Test getting non-existent team returns 404."""
        import uuid
        fake_id = uuid.uuid4()
        response = authenticated_client.get(f'/api/v1/teams/{fake_id}/')

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_team_as_leader(self, authenticated_client, team):
        """Test updating team as leader."""
        response = authenticated_client.patch(f'/api/v1/teams/{team.id}/', {
            'name': 'Updated Team Name',
            'description': 'Updated description'
        })

        assert response.status_code == status.HTTP_200_OK
        team.refresh_from_db()
        assert team.name == 'Updated Team Name'

    def test_update_team_as_member_forbidden(self, api_client, team, create_user):
        """Test member cannot update team."""
        member = create_user(email='member@example.com')
        TeamMembership.objects.create(
            team=team,
            user=member,
            role=TeamMembership.ROLE_MEMBER,
            status=TeamMembership.STATUS_ACTIVE
        )

        # Authenticate as member
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(member)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        response = api_client.patch(f'/api/v1/teams/{team.id}/', {
            'name': 'Should Not Change'
        })

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_team_as_leader(self, authenticated_client, team):
        """Test soft delete team as leader."""
        response = authenticated_client.delete(f'/api/v1/teams/{team.id}/')

        assert response.status_code == status.HTTP_200_OK
        team.refresh_from_db()
        assert team.is_deleted

    def test_delete_team_as_member_forbidden(self, api_client, team, create_user):
        """Test member cannot delete team."""
        member = create_user(email='member@example.com')
        TeamMembership.objects.create(
            team=team,
            user=member,
            role=TeamMembership.ROLE_MEMBER,
            status=TeamMembership.STATUS_ACTIVE
        )

        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(member)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        response = api_client.delete(f'/api/v1/teams/{team.id}/')

        assert response.status_code == status.HTTP_403_FORBIDDEN


# ============================================================================
# Team Members API Tests
# ============================================================================

@pytest.mark.django_db
class TestTeamMembersAPI:
    """Test cases for team members endpoint."""

    def test_list_team_members(self, authenticated_client, team, create_user):
        """Test listing team members."""
        # Add a member
        member = create_user(email='member@example.com')
        TeamMembership.objects.create(
            team=team,
            user=member,
            role=TeamMembership.ROLE_MEMBER,
            status=TeamMembership.STATUS_ACTIVE
        )

        response = authenticated_client.get(f'/api/v1/teams/{team.id}/members/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 2  # Leader + Member

    def test_list_members_non_member(self, api_client, team, create_user):
        """Test non-member cannot list team members."""
        non_member = create_user(email='nonmember@example.com')

        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(non_member)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        response = api_client.get(f'/api/v1/teams/{team.id}/members/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 0  # Empty for non-members


# ============================================================================
# Invitation API Tests
# ============================================================================

@pytest.mark.django_db
class TestInvitationAPI:
    """Test cases for team invitation endpoints."""

    def test_invite_member(self, authenticated_client, team, create_user):
        """Test inviting a member to team."""
        invitee = create_user(email='invitee@example.com')

        with patch('apps.teams.views.send_team_invitation'):
            response = authenticated_client.post(f'/api/v1/teams/{team.id}/invite/', {
                'email': invitee.email,
                'role': 'member'
            })

        assert response.status_code == status.HTTP_201_CREATED
        assert 'invitation sent' in response.data['message'].lower()

    def test_invite_witness(self, authenticated_client, team, create_user):
        """Test inviting a witness to team."""
        witness = create_user(email='witness@example.com')

        with patch('apps.teams.views.send_team_invitation'):
            response = authenticated_client.post(f'/api/v1/teams/{team.id}/invite/', {
                'email': witness.email,
                'role': 'witness'
            })

        assert response.status_code == status.HTTP_201_CREATED

    def test_invite_as_member_forbidden(self, api_client, team, create_user):
        """Test member cannot invite."""
        member = create_user(email='member@example.com')
        invitee = create_user(email='invitee@example.com')

        TeamMembership.objects.create(
            team=team,
            user=member,
            role=TeamMembership.ROLE_MEMBER,
            status=TeamMembership.STATUS_ACTIVE
        )

        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(member)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        response = api_client.post(f'/api/v1/teams/{team.id}/invite/', {
            'email': invitee.email,
            'role': 'member'
        })

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_accept_invitation(self, api_client, team, create_user, user):
        """Test accepting team invitation."""
        invitee = create_user(email='invitee@example.com')
        membership = TeamMembership.objects.create(
            team=team,
            user=invitee,
            role=TeamMembership.ROLE_MEMBER,
            status=TeamMembership.STATUS_PENDING,
            invited_by=user,
            invitation_token='test-invitation-token',
            invitation_expires_at=timezone.now() + timedelta(days=7)
        )

        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(invitee)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        with patch('apps.teams.views.send_invitation_accepted_notification'):
            response = api_client.post('/api/v1/teams/accept-invitation/', {
                'token': 'test-invitation-token'
            })

        assert response.status_code == status.HTTP_200_OK
        membership.refresh_from_db()
        assert membership.status == TeamMembership.STATUS_ACTIVE

    def test_decline_invitation(self, api_client, team, create_user, user):
        """Test declining team invitation."""
        invitee = create_user(email='invitee@example.com')
        membership = TeamMembership.objects.create(
            team=team,
            user=invitee,
            role=TeamMembership.ROLE_MEMBER,
            status=TeamMembership.STATUS_PENDING,
            invited_by=user,
            invitation_token='decline-token'
        )

        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(invitee)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        response = api_client.post('/api/v1/teams/decline-invitation/', {
            'token': 'decline-token'
        })

        assert response.status_code == status.HTTP_200_OK
        assert not TeamMembership.objects.filter(id=membership.id).exists()

    def test_pending_invitations(self, api_client, team, create_user, user):
        """Test listing pending invitations."""
        invitee = create_user(email='invitee@example.com')
        TeamMembership.objects.create(
            team=team,
            user=invitee,
            role=TeamMembership.ROLE_MEMBER,
            status=TeamMembership.STATUS_PENDING,
            invited_by=user,
            invitation_token='pending-token',
            invitation_sent_at=timezone.now()
        )

        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(invitee)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        response = api_client.get('/api/v1/teams/invitations/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['invitations']) == 1


# ============================================================================
# Leave Team API Tests
# ============================================================================

@pytest.mark.django_db
class TestLeaveTeamAPI:
    """Test cases for leaving team endpoint."""

    def test_member_leave_team(self, api_client, team, create_user, user):
        """Test member can leave team."""
        member = create_user(email='member@example.com')
        membership = TeamMembership.objects.create(
            team=team,
            user=member,
            role=TeamMembership.ROLE_MEMBER,
            status=TeamMembership.STATUS_ACTIVE
        )

        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(member)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        with patch('apps.teams.views.send_member_left_notification'):
            response = api_client.post(f'/api/v1/teams/{team.id}/leave/')

        assert response.status_code == status.HTTP_200_OK
        membership.refresh_from_db()
        assert membership.status == TeamMembership.STATUS_LEFT

    def test_leader_cannot_leave_team(self, authenticated_client, team):
        """Test leader cannot leave team without transferring leadership."""
        response = authenticated_client.post(f'/api/v1/teams/{team.id}/leave/')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'leader' in response.data['error'].lower()


# ============================================================================
# Remove Member API Tests
# ============================================================================

@pytest.mark.django_db
class TestRemoveMemberAPI:
    """Test cases for removing team members."""

    def test_leader_remove_member(self, authenticated_client, team, create_user):
        """Test leader can remove member."""
        member = create_user(email='member@example.com')
        membership = TeamMembership.objects.create(
            team=team,
            user=member,
            role=TeamMembership.ROLE_MEMBER,
            status=TeamMembership.STATUS_ACTIVE
        )

        response = authenticated_client.post(f'/api/v1/teams/{team.id}/remove-member/', {
            'user_id': str(member.id)
        })

        assert response.status_code == status.HTTP_200_OK
        membership.refresh_from_db()
        assert membership.status == TeamMembership.STATUS_LEFT

    def test_leader_cannot_remove_self(self, authenticated_client, team, user):
        """Test leader cannot remove themselves."""
        response = authenticated_client.post(f'/api/v1/teams/{team.id}/remove-member/', {
            'user_id': str(user.id)
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_member_cannot_remove_others(self, api_client, team, create_user):
        """Test member cannot remove other members."""
        member = create_user(email='member@example.com')
        other_member = create_user(email='other@example.com')

        for m in [member, other_member]:
            TeamMembership.objects.create(
                team=team,
                user=m,
                role=TeamMembership.ROLE_MEMBER,
                status=TeamMembership.STATUS_ACTIVE
            )

        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(member)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        response = api_client.post(f'/api/v1/teams/{team.id}/remove-member/', {
            'user_id': str(other_member.id)
        })

        assert response.status_code == status.HTTP_403_FORBIDDEN


# ============================================================================
# Transfer Leadership API Tests
# ============================================================================

@pytest.mark.django_db
class TestTransferLeadershipAPI:
    """Test cases for transferring team leadership."""

    def test_transfer_leadership(self, authenticated_client, team, create_user, user):
        """Test leader can transfer leadership."""
        new_leader = create_user(email='newleader@example.com')
        TeamMembership.objects.create(
            team=team,
            user=new_leader,
            role=TeamMembership.ROLE_MEMBER,
            status=TeamMembership.STATUS_ACTIVE
        )

        response = authenticated_client.post(f'/api/v1/teams/{team.id}/transfer-leadership/', {
            'user_id': str(new_leader.id)
        })

        assert response.status_code == status.HTTP_200_OK

        team.refresh_from_db()
        assert team.created_by == new_leader

        # Old leader is now member
        old_leader_membership = team.memberships.get(user=user)
        assert old_leader_membership.role == TeamMembership.ROLE_MEMBER

        # New leader is leader
        new_leader_membership = team.memberships.get(user=new_leader)
        assert new_leader_membership.role == TeamMembership.ROLE_LEADER

    def test_cannot_transfer_to_witness(self, authenticated_client, team, create_user):
        """Test cannot transfer leadership to witness."""
        witness = create_user(email='witness@example.com')
        TeamMembership.objects.create(
            team=team,
            user=witness,
            role=TeamMembership.ROLE_WITNESS,
            status=TeamMembership.STATUS_ACTIVE
        )

        response = authenticated_client.post(f'/api/v1/teams/{team.id}/transfer-leadership/', {
            'user_id': str(witness.id)
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_member_cannot_transfer_leadership(self, api_client, team, create_user, user):
        """Test member cannot transfer leadership."""
        member = create_user(email='member@example.com')
        other_member = create_user(email='other@example.com')

        for m in [member, other_member]:
            TeamMembership.objects.create(
                team=team,
                user=m,
                role=TeamMembership.ROLE_MEMBER,
                status=TeamMembership.STATUS_ACTIVE
            )

        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(member)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        response = api_client.post(f'/api/v1/teams/{team.id}/transfer-leadership/', {
            'user_id': str(other_member.id)
        })

        assert response.status_code == status.HTTP_403_FORBIDDEN


# ============================================================================
# Update Membership API Tests
# ============================================================================

@pytest.mark.django_db
class TestUpdateMembershipAPI:
    """Test cases for updating team membership."""

    def test_leader_update_member_role(self, authenticated_client, team, create_user):
        """Test leader can update member role."""
        member = create_user(email='member@example.com')
        membership = TeamMembership.objects.create(
            team=team,
            user=member,
            role=TeamMembership.ROLE_MEMBER,
            status=TeamMembership.STATUS_ACTIVE
        )

        response = authenticated_client.patch(
            f'/api/v1/teams/{team.id}/members/{membership.id}/',
            {'is_default_guardian': False}
        )

        assert response.status_code == status.HTTP_200_OK

    def test_member_cannot_update_membership(self, api_client, team, create_user, user):
        """Test member cannot update memberships."""
        member = create_user(email='member@example.com')
        other_member = create_user(email='other@example.com')

        member_membership = TeamMembership.objects.create(
            team=team,
            user=member,
            role=TeamMembership.ROLE_MEMBER,
            status=TeamMembership.STATUS_ACTIVE
        )
        other_membership = TeamMembership.objects.create(
            team=team,
            user=other_member,
            role=TeamMembership.ROLE_MEMBER,
            status=TeamMembership.STATUS_ACTIVE
        )

        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(member)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        response = api_client.patch(
            f'/api/v1/teams/{team.id}/members/{other_membership.id}/',
            {'role': 'witness'}
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
