"""
AWFM Teams App - URL Configuration

Team management endpoints.
"""

from django.urls import path
from .views import (
    TeamListCreateView,
    TeamDetailView,
    TeamMembersView,
    InviteMemberView,
    AcceptInvitationView,
    DeclineInvitationView,
    LeaveTeamView,
    RemoveMemberView,
    UpdateMembershipView,
    TransferLeadershipView,
    PendingInvitationsView,
    ValidatePendingInvitationView,
    ClaimPendingInvitationView,
)

urlpatterns = [
    # Team CRUD
    path('', TeamListCreateView.as_view(), name='team-list-create'),
    path('<uuid:id>/', TeamDetailView.as_view(), name='team-detail'),

    # Team Members
    path('<uuid:id>/members/', TeamMembersView.as_view(), name='team-members'),
    path('<uuid:id>/members/<uuid:membership_id>/', UpdateMembershipView.as_view(), name='update-membership'),

    # Invitations
    path('invitations/', PendingInvitationsView.as_view(), name='pending-invitations'),
    path('<uuid:id>/invite/', InviteMemberView.as_view(), name='invite-member'),
    path('accept-invitation/', AcceptInvitationView.as_view(), name='accept-invitation'),
    path('decline-invitation/', DeclineInvitationView.as_view(), name='decline-invitation'),
    path('validate-invitation/', ValidatePendingInvitationView.as_view(), name='validate-pending-invitation'),
    path('claim-invitation/', ClaimPendingInvitationView.as_view(), name='claim-pending-invitation'),

    # Team Actions
    path('<uuid:id>/leave/', LeaveTeamView.as_view(), name='leave-team'),
    path('<uuid:id>/remove-member/', RemoveMemberView.as_view(), name='remove-member'),
    path('<uuid:id>/transfer-leadership/', TransferLeadershipView.as_view(), name='transfer-leadership'),
]
