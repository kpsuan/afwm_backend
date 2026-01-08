"""
AWFM Teams App - Views

Team management views for creating teams, inviting members, and managing memberships.
"""

import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Prefetch
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Team, TeamMembership, PendingInvitation
from .serializers import (
    TeamSerializer,
    CreateTeamSerializer,
    TeamMemberSerializer,
    InviteMemberSerializer,
    AcceptInvitationSerializer,
    UpdateMembershipSerializer,
    PendingInvitationSerializer,
)
from .emails import (
    send_team_invitation,
    send_signup_invitation,
    send_invitation_accepted_notification,
    send_member_left_notification,
)
from apps.communication.notifications import (
    notify_team_invitation,
    notify_invitation_accepted,
    notify_member_left,
    notify_member_joined,
)

User = get_user_model()


class TeamListCreateView(generics.ListCreateAPIView):
    """
    List teams the user is a member of, or create a new team.

    GET /api/v1/teams/
    - Returns all teams where user is an active member

    POST /api/v1/teams/
    - Creates a new team with user as leader
    - Request: { "name": "My Care Team", "description": "...", "team_level": 1 }
    """
    permission_classes = (IsAuthenticated,)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateTeamSerializer
        return TeamSerializer

    def get_queryset(self):
        """Return teams where user is an active member.

        Optimized with prefetch_related and select_related to avoid N+1 queries.
        """
        return Team.objects.filter(
            memberships__user=self.request.user,
            memberships__status=TeamMembership.STATUS_ACTIVE,
            deleted_at__isnull=True
        ).distinct().select_related(
            'created_by'
        ).prefetch_related(
            Prefetch(
                'memberships',
                queryset=TeamMembership.objects.filter(
                    status__in=['active', 'pending']
                ).select_related('user'),
            )
        ).order_by('-created_at')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        team = serializer.save()

        # Return full team data
        response_serializer = TeamSerializer(team, context={'request': request})
        return Response({
            'team': response_serializer.data,
            'message': 'Team created successfully'
        }, status=status.HTTP_201_CREATED)


class TeamDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Get, update, or delete a specific team.

    GET /api/v1/teams/{id}/
    PUT/PATCH /api/v1/teams/{id}/
    DELETE /api/v1/teams/{id}/ (soft delete, leader only)
    """
    permission_classes = (IsAuthenticated,)
    serializer_class = TeamSerializer
    lookup_field = 'id'

    def get_queryset(self):
        """Return teams where user is an active member."""
        return Team.objects.filter(
            memberships__user=self.request.user,
            memberships__status=TeamMembership.STATUS_ACTIVE,
            deleted_at__isnull=True
        ).distinct()

    def update(self, request, *args, **kwargs):
        """Only leader can update team."""
        team = self.get_object()
        membership = team.memberships.filter(
            user=request.user,
            status=TeamMembership.STATUS_ACTIVE
        ).first()

        if not membership or membership.role != TeamMembership.ROLE_LEADER:
            return Response({
                'error': 'Only the team leader can update team details'
            }, status=status.HTTP_403_FORBIDDEN)

        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Soft delete team (leader only, requires password confirmation)."""
        team = self.get_object()
        membership = team.memberships.filter(
            user=request.user,
            status=TeamMembership.STATUS_ACTIVE
        ).first()

        if not membership or membership.role != TeamMembership.ROLE_LEADER:
            return Response({
                'error': 'Only the team leader can delete the team'
            }, status=status.HTTP_403_FORBIDDEN)

        # Verify password
        password = request.data.get('password')
        if not password:
            return Response({
                'error': 'Password is required to confirm deletion'
            }, status=status.HTTP_400_BAD_REQUEST)

        if not request.user.check_password(password):
            return Response({
                'error': 'Incorrect password'
            }, status=status.HTTP_400_BAD_REQUEST)

        team.soft_delete()
        return Response({
            'message': 'Team deleted successfully'
        }, status=status.HTTP_200_OK)


class TeamMembersView(APIView):
    """
    List all members of a team, including pending invitations for non-registered users.

    GET /api/v1/teams/{id}/members/
    """
    permission_classes = (IsAuthenticated,)

    def get(self, request, id):
        # Verify user is a member of this team
        team = Team.objects.filter(
            id=id,
            memberships__user=request.user,
            memberships__status=TeamMembership.STATUS_ACTIVE,
            deleted_at__isnull=True
        ).first()

        if not team:
            return Response([], status=status.HTTP_200_OK)

        # Get team memberships (existing users)
        memberships = team.memberships.filter(
            status__in=['active', 'pending']
        ).select_related('user', 'invited_by').order_by('role', 'created_at')

        members_data = TeamMemberSerializer(memberships, many=True).data

        # Get pending invitations (non-registered users)
        pending_invitations = team.pending_invitations.select_related('invited_by').order_by('created_at')

        for invitation in pending_invitations:
            members_data.append({
                'id': str(invitation.id),
                'email': invitation.email,
                'display_name': None,
                'role': invitation.role,
                'status': 'pending',
                'is_pending_signup': True,  # Flag to indicate this is a non-registered user
                'invited_by': {
                    'id': str(invitation.invited_by.id) if invitation.invited_by else None,
                    'display_name': invitation.invited_by.display_name if invitation.invited_by else None,
                },
                'created_at': invitation.created_at.isoformat(),
                'expires_at': invitation.expires_at.isoformat(),
            })

        return Response(members_data, status=status.HTTP_200_OK)


class InviteMemberView(APIView):
    """
    Invite a member to the team.

    POST /api/v1/teams/{id}/invite/
    Request: { "email": "user@example.com", "role": "member", "message": "optional custom message" }

    If the user exists, creates a TeamMembership with pending status.
    If the user doesn't exist, creates a PendingInvitation and sends a signup link.
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request, id):
        # Get team and verify user is leader
        try:
            team = Team.objects.get(id=id, deleted_at__isnull=True)
        except Team.DoesNotExist:
            return Response({
                'error': 'Team not found'
            }, status=status.HTTP_404_NOT_FOUND)

        membership = team.memberships.filter(
            user=request.user,
            status=TeamMembership.STATUS_ACTIVE
        ).first()

        if not membership or membership.role != TeamMembership.ROLE_LEADER:
            return Response({
                'error': 'Only the team leader can invite members'
            }, status=status.HTTP_403_FORBIDDEN)

        # Basic validation
        email = request.data.get('email', '').strip().lower()
        role = request.data.get('role', TeamMembership.ROLE_MEMBER)
        custom_message = request.data.get('message', '')

        if not email:
            return Response({
                'error': 'Email is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        if role not in [TeamMembership.ROLE_MEMBER, TeamMembership.ROLE_WITNESS]:
            return Response({
                'error': 'Invalid role. Must be "member" or "witness"'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check if already a member or has pending invitation
        if team.memberships.filter(user__email=email).exclude(status='left').exists():
            return Response({
                'error': 'This user is already a member or has a pending invitation'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check if there's already a pending invitation for this email
        if PendingInvitation.objects.filter(email=email, team=team).exists():
            return Response({
                'error': 'An invitation has already been sent to this email'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Create invitation token
        token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(days=7)
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')

        # Check if user exists
        try:
            invitee = User.objects.get(email=email)

            # User exists - create TeamMembership
            new_membership = TeamMembership.objects.create(
                team=team,
                user=invitee,
                role=role,
                status=TeamMembership.STATUS_PENDING,
                invited_by=request.user,
                invitation_token=token,
                invitation_sent_at=timezone.now(),
                invitation_expires_at=expires_at,
                is_default_guardian=True,
                is_default_emergency_contact=True,
            )

            # Send invitation email
            invitation_url = f"{frontend_url}/accept-invitation?token={token}"
            send_team_invitation(invitee, team, request.user, invitation_url)

            # Send real-time notification
            notify_team_invitation(invitee, team, request.user, invitation_token=token)

            return Response({
                'message': f'Invitation sent to {email}',
                'membership': TeamMemberSerializer(new_membership).data,
                'user_exists': True
            }, status=status.HTTP_201_CREATED)

        except User.DoesNotExist:
            # User doesn't exist - create PendingInvitation
            pending_invitation = PendingInvitation.objects.create(
                email=email,
                team=team,
                role=role,
                invited_by=request.user,
                message=custom_message,
                invitation_token=token,
                expires_at=expires_at,
            )

            # Send signup invitation email
            signup_url = f"{frontend_url}/register?invitation={token}"
            send_signup_invitation(email, team, request.user, signup_url, custom_message)

            return Response({
                'message': f'Signup invitation sent to {email}',
                'pending_invitation': PendingInvitationSerializer(pending_invitation).data,
                'user_exists': False
            }, status=status.HTTP_201_CREATED)


class AcceptInvitationView(APIView):
    """
    Accept a team invitation.

    POST /api/v1/teams/accept-invitation/
    Request: { "token": "..." }
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = AcceptInvitationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data['token']
        membership = TeamMembership.objects.get(invitation_token=token)

        # Verify the invitation is for this user
        if membership.user != request.user:
            return Response({
                'error': 'This invitation is for a different user'
            }, status=status.HTTP_403_FORBIDDEN)

        # Accept the invitation
        membership.accept_invitation()

        # Notify team leader
        leader_membership = membership.team.get_leader()
        if leader_membership:
            send_invitation_accepted_notification(
                leader_membership.user,
                request.user,
                membership.team
            )
            # Send real-time notification
            notify_invitation_accepted(leader_membership.user, request.user, membership.team)

        return Response({
            'message': 'Invitation accepted successfully',
            'team': TeamSerializer(membership.team, context={'request': request}).data
        }, status=status.HTTP_200_OK)


class DeclineInvitationView(APIView):
    """
    Decline a team invitation.

    POST /api/v1/teams/decline-invitation/
    Request: { "token": "..." }
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        token = request.data.get('token')

        if not token:
            return Response({
                'error': 'Invitation token is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            membership = TeamMembership.objects.get(
                invitation_token=token,
                status=TeamMembership.STATUS_PENDING
            )
        except TeamMembership.DoesNotExist:
            return Response({
                'error': 'Invalid or expired invitation'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Verify the invitation is for this user
        if membership.user != request.user:
            return Response({
                'error': 'This invitation is for a different user'
            }, status=status.HTTP_403_FORBIDDEN)

        # Delete the pending membership
        membership.delete()

        return Response({
            'message': 'Invitation declined'
        }, status=status.HTTP_200_OK)


class LeaveTeamView(APIView):
    """
    Leave a team.

    POST /api/v1/teams/{id}/leave/
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request, id):
        try:
            team = Team.objects.get(id=id, deleted_at__isnull=True)
        except Team.DoesNotExist:
            return Response({
                'error': 'Team not found'
            }, status=status.HTTP_404_NOT_FOUND)

        membership = team.memberships.filter(
            user=request.user,
            status=TeamMembership.STATUS_ACTIVE
        ).first()

        if not membership:
            return Response({
                'error': 'You are not a member of this team'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Leaders cannot leave (must transfer leadership or delete team)
        if membership.role == TeamMembership.ROLE_LEADER:
            return Response({
                'error': 'Team leaders cannot leave. Transfer leadership or delete the team.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Leave the team
        membership.leave_team()

        # Notify team leader
        leader_membership = team.get_leader()
        if leader_membership:
            send_member_left_notification(
                leader_membership.user,
                request.user,
                team
            )
            # Send real-time notification
            notify_member_left(leader_membership.user, request.user, team)

        return Response({
            'message': 'You have left the team'
        }, status=status.HTTP_200_OK)


class RemoveMemberView(APIView):
    """
    Remove a member from the team (leader only).

    POST /api/v1/teams/{id}/remove-member/
    Request: { "user_id": "..." }
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request, id):
        try:
            team = Team.objects.get(id=id, deleted_at__isnull=True)
        except Team.DoesNotExist:
            return Response({
                'error': 'Team not found'
            }, status=status.HTTP_404_NOT_FOUND)

        # Verify requester is leader
        leader_membership = team.memberships.filter(
            user=request.user,
            role=TeamMembership.ROLE_LEADER,
            status=TeamMembership.STATUS_ACTIVE
        ).first()

        if not leader_membership:
            return Response({
                'error': 'Only the team leader can remove members'
            }, status=status.HTTP_403_FORBIDDEN)

        user_id = request.data.get('user_id')
        if not user_id:
            return Response({
                'error': 'user_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Cannot remove yourself
        if str(request.user.id) == str(user_id):
            return Response({
                'error': 'Cannot remove yourself. Use leave team or delete team instead.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Find the membership to remove
        membership = team.memberships.filter(
            user_id=user_id,
            status__in=[TeamMembership.STATUS_ACTIVE, TeamMembership.STATUS_PENDING]
        ).first()

        if not membership:
            return Response({
                'error': 'Member not found in this team'
            }, status=status.HTTP_404_NOT_FOUND)

        # Mark as left
        membership.leave_team()

        return Response({
            'message': 'Member removed from team'
        }, status=status.HTTP_200_OK)


class UpdateMembershipView(APIView):
    """
    Update a member's role or settings (leader only).

    PATCH /api/v1/teams/{id}/members/{membership_id}/
    Request: { "role": "member", "is_default_guardian": true }
    """
    permission_classes = (IsAuthenticated,)

    def patch(self, request, id, membership_id):
        try:
            team = Team.objects.get(id=id, deleted_at__isnull=True)
        except Team.DoesNotExist:
            return Response({
                'error': 'Team not found'
            }, status=status.HTTP_404_NOT_FOUND)

        # Verify requester is leader
        leader_membership = team.memberships.filter(
            user=request.user,
            role=TeamMembership.ROLE_LEADER,
            status=TeamMembership.STATUS_ACTIVE
        ).first()

        if not leader_membership:
            return Response({
                'error': 'Only the team leader can update member settings'
            }, status=status.HTTP_403_FORBIDDEN)

        # Get the membership to update
        try:
            membership = team.memberships.get(id=membership_id)
        except TeamMembership.DoesNotExist:
            return Response({
                'error': 'Membership not found'
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = UpdateMembershipSerializer(membership, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({
            'message': 'Membership updated',
            'membership': TeamMemberSerializer(membership).data
        }, status=status.HTTP_200_OK)


class TransferLeadershipView(APIView):
    """
    Transfer team leadership to another member.

    POST /api/v1/teams/{id}/transfer-leadership/
    Request: { "user_id": "..." }
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request, id):
        try:
            team = Team.objects.get(id=id, deleted_at__isnull=True)
        except Team.DoesNotExist:
            return Response({
                'error': 'Team not found'
            }, status=status.HTTP_404_NOT_FOUND)

        # Verify requester is current leader
        current_leader = team.memberships.filter(
            user=request.user,
            role=TeamMembership.ROLE_LEADER,
            status=TeamMembership.STATUS_ACTIVE
        ).first()

        if not current_leader:
            return Response({
                'error': 'Only the current team leader can transfer leadership'
            }, status=status.HTTP_403_FORBIDDEN)

        user_id = request.data.get('user_id')
        if not user_id:
            return Response({
                'error': 'user_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Find the new leader
        new_leader = team.memberships.filter(
            user_id=user_id,
            status=TeamMembership.STATUS_ACTIVE
        ).exclude(role=TeamMembership.ROLE_WITNESS).first()

        if not new_leader:
            return Response({
                'error': 'User not found or is a witness (witnesses cannot be leaders)'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Transfer leadership
        current_leader.role = TeamMembership.ROLE_MEMBER
        current_leader.save(update_fields=['role', 'updated_at'])

        new_leader.role = TeamMembership.ROLE_LEADER
        new_leader.save(update_fields=['role', 'updated_at'])

        # Update team created_by
        team.created_by = new_leader.user
        team.save(update_fields=['created_by', 'updated_at'])

        return Response({
            'message': f'Leadership transferred to {new_leader.user.display_name}',
            'team': TeamSerializer(team, context={'request': request}).data
        }, status=status.HTTP_200_OK)


class PendingInvitationsView(generics.ListAPIView):
    """
    List pending invitations for the current user.

    GET /api/v1/teams/invitations/
    """
    permission_classes = (IsAuthenticated,)
    serializer_class = TeamMemberSerializer

    def get_queryset(self):
        return TeamMembership.objects.filter(
            user=self.request.user,
            status=TeamMembership.STATUS_PENDING,
            team__deleted_at__isnull=True
        ).select_related('team', 'invited_by')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        invitations = []

        for membership in queryset:
            invitations.append({
                'id': str(membership.id),
                'token': membership.invitation_token,
                'team': {
                    'id': str(membership.team.id),
                    'name': membership.team.name,
                    'description': membership.team.description,
                },
                'role': membership.role,
                'invited_by': {
                    'id': str(membership.invited_by.id) if membership.invited_by else None,
                    'display_name': membership.invited_by.display_name if membership.invited_by else None,
                },
                'invited_at': membership.invitation_sent_at,
                'expires_at': membership.invitation_expires_at,
            })

        return Response({'invitations': invitations})


class ValidatePendingInvitationView(APIView):
    """
    Validate a pending invitation token (for signup page).

    GET /api/v1/teams/validate-invitation/?token=...

    This is a public endpoint that returns invitation details
    so the signup page can show who invited them and to which team.
    """
    permission_classes = (AllowAny,)

    def get(self, request):
        token = request.query_params.get('token')

        if not token:
            return Response({
                'error': 'Invitation token is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            invitation = PendingInvitation.objects.select_related(
                'team', 'invited_by'
            ).get(invitation_token=token)
        except PendingInvitation.DoesNotExist:
            return Response({
                'error': 'Invalid or expired invitation'
            }, status=status.HTTP_404_NOT_FOUND)

        # Check if expired
        if invitation.is_expired:
            return Response({
                'error': 'This invitation has expired'
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'valid': True,
            'invitation': {
                'email': invitation.email,
                'team': {
                    'id': str(invitation.team.id),
                    'name': invitation.team.name,
                    'description': invitation.team.description,
                },
                'role': invitation.role,
                'invited_by': {
                    'id': str(invitation.invited_by.id),
                    'display_name': invitation.invited_by.display_name,
                },
                'message': invitation.message,
                'expires_at': invitation.expires_at.isoformat(),
            }
        }, status=status.HTTP_200_OK)


class ClaimPendingInvitationView(APIView):
    """
    Claim a pending invitation after signup.

    POST /api/v1/teams/claim-invitation/
    Request: { "token": "..." }

    Converts the PendingInvitation to a TeamMembership for the logged-in user.
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        token = request.data.get('token')

        if not token:
            return Response({
                'error': 'Invitation token is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            invitation = PendingInvitation.objects.select_related(
                'team', 'invited_by'
            ).get(invitation_token=token)
        except PendingInvitation.DoesNotExist:
            return Response({
                'error': 'Invalid or expired invitation'
            }, status=status.HTTP_404_NOT_FOUND)

        # Check if expired
        if invitation.is_expired:
            invitation.delete()  # Clean up expired invitation
            return Response({
                'error': 'This invitation has expired'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Verify the invitation email matches the user's email
        if invitation.email.lower() != request.user.email.lower():
            return Response({
                'error': 'This invitation was sent to a different email address'
            }, status=status.HTTP_403_FORBIDDEN)

        # Check if user is already a member
        if invitation.team.memberships.filter(user=request.user).exclude(status='left').exists():
            invitation.delete()  # Clean up since they're already a member
            return Response({
                'error': 'You are already a member of this team'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Convert to membership
        membership = invitation.convert_to_membership(request.user)

        # Notify team leader
        leader_membership = membership.team.get_leader()
        if leader_membership:
            send_invitation_accepted_notification(
                leader_membership.user,
                request.user,
                membership.team
            )
            # Send real-time notification (new member joined via signup)
            notify_member_joined(leader_membership.user, request.user, membership.team)

        return Response({
            'message': f'Welcome to {membership.team.name}!',
            'team': TeamSerializer(membership.team, context={'request': request}).data,
            'membership': TeamMemberSerializer(membership).data
        }, status=status.HTTP_201_CREATED)
