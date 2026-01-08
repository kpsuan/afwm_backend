"""
AWFM Backend - Pytest Configuration and Fixtures

This module contains shared fixtures for all tests.
"""

import pytest
import uuid
from datetime import timedelta
from django.utils import timezone


@pytest.fixture
def api_client():
    """Return a DRF API client."""
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def user_data():
    """Return valid user registration data."""
    return {
        'email': 'testuser@example.com',
        'password': 'SecurePass123!',
        'display_name': 'Test User',
        'first_name': 'Test',
        'last_name': 'User',
    }


@pytest.fixture
def create_user(db):
    """Factory fixture to create users."""
    from apps.accounts.models import User

    def _create_user(
        email='testuser@example.com',
        password='SecurePass123!',
        display_name='Test User',
        email_verified=True,
        is_active=True,
        **kwargs
    ):
        user = User.objects.create_user(
            email=email,
            password=password,
            display_name=display_name,
            **kwargs
        )
        user.email_verified = email_verified
        user.is_active = is_active
        user.save()
        return user

    return _create_user


@pytest.fixture
def user(create_user):
    """Create and return a single test user."""
    return create_user()


@pytest.fixture
def authenticated_client(api_client, user):
    """Return an API client with authenticated user."""
    from rest_framework_simplejwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


@pytest.fixture
def create_team(db, user):
    """Factory fixture to create teams."""
    from apps.teams.models import Team, TeamMembership

    def _create_team(
        name='Test Team',
        description='A test care team',
        created_by=None,
        add_leader_membership=True,
        **kwargs
    ):
        creator = created_by or user
        team = Team.objects.create(
            name=name,
            description=description,
            created_by=creator,
            **kwargs
        )

        if add_leader_membership:
            TeamMembership.objects.create(
                team=team,
                user=creator,
                role=TeamMembership.ROLE_LEADER,
                status=TeamMembership.STATUS_ACTIVE,
                is_default_guardian=True,
                is_default_emergency_contact=True,
                joined_at=timezone.now()
            )

        return team

    return _create_team


@pytest.fixture
def team(create_team):
    """Create and return a single test team."""
    return create_team()


@pytest.fixture
def create_question(db):
    """Factory fixture to create questions."""
    from apps.content.models import Question

    def _create_question(
        id=None,
        title='Test Question',
        question_text='What is your test preference?',
        display_order=1,
        batch_number=1,
        **kwargs
    ):
        question_id = id or f'Q{uuid.uuid4().hex[:4].upper()}'
        return Question.objects.create(
            id=question_id,
            title=title,
            question_text=question_text,
            display_order=display_order,
            batch_number=batch_number,
            **kwargs
        )

    return _create_question


@pytest.fixture
def question(create_question):
    """Create and return a single test question."""
    return create_question(id='Q10A')


@pytest.fixture
def create_layer(db, question):
    """Factory fixture to create layers."""
    from apps.content.models import Layer

    def _create_layer(
        question_ref=None,
        layer_number=1,
        layer_title='YOUR POSITION',
        layer_question='What is your position on this?',
        selection_type='single',
        **kwargs
    ):
        q = question_ref or question
        return Layer.objects.create(
            question=q,
            layer_number=layer_number,
            layer_title=layer_title,
            layer_question=layer_question,
            selection_type=selection_type,
            components_at_selection=['C1', 'C3'],
            components_at_confirmation=['C2', 'C4'],
            **kwargs
        )

    return _create_layer


@pytest.fixture
def layer(create_layer):
    """Create and return a single test layer."""
    return create_layer()


@pytest.fixture
def create_option(db, question, layer):
    """Factory fixture to create options."""
    from apps.content.models import Option

    def _create_option(
        question_ref=None,
        layer_ref=None,
        option_number=1,
        option_text='Test option text',
        display_order=1,
        **kwargs
    ):
        q = question_ref or question
        l = layer_ref or layer
        return Option.objects.create(
            question=q,
            layer=l,
            option_number=option_number,
            option_text=option_text,
            display_order=display_order,
            **kwargs
        )

    return _create_option


@pytest.fixture
def option(create_option):
    """Create and return a single test option."""
    return create_option()


@pytest.fixture
def create_component(db, option):
    """Factory fixture to create components."""
    from apps.content.models import Component

    def _create_component(
        option_ref=None,
        component_type='C1',
        component_text='This is the component text.',
        **kwargs
    ):
        opt = option_ref or option
        return Component.objects.create(
            option=opt,
            component_type=component_type,
            component_text=component_text,
            **kwargs
        )

    return _create_component


@pytest.fixture
def component(create_component):
    """Create and return a single test component."""
    return create_component()


@pytest.fixture
def create_response(db, user, question, layer, option):
    """Factory fixture to create user responses."""
    from apps.responses.models import Response

    def _create_response(
        user_ref=None,
        question_ref=None,
        layer_ref=None,
        selected_option_ids=None,
        completed_at=None,
        **kwargs
    ):
        u = user_ref or user
        q = question_ref or question
        l = layer_ref or layer
        opts = selected_option_ids or [option.id]

        return Response.objects.create(
            user=u,
            question=q,
            layer=l,
            selected_option_ids=opts,
            completed_at=completed_at,
            **kwargs
        )

    return _create_response


@pytest.fixture
def response_obj(create_response):
    """Create and return a single test response."""
    return create_response()


@pytest.fixture
def create_questionnaire_progress(db, user, question):
    """Factory fixture to create questionnaire progress."""
    from apps.responses.models import QuestionnaireProgress

    def _create_progress(
        user_ref=None,
        question_ref=None,
        current_phase='q1_selection',
        current_layer=1,
        is_completed=False,
        **kwargs
    ):
        u = user_ref or user
        q = question_ref or question

        return QuestionnaireProgress.objects.create(
            user=u,
            question=q,
            current_phase=current_phase,
            current_layer=current_layer,
            is_completed=is_completed,
            **kwargs
        )

    return _create_progress
