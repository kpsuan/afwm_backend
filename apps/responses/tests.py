"""
AWFM Responses App - Test Cases

Comprehensive tests for user responses and questionnaire progress tracking.
"""

import pytest
from datetime import timedelta
from django.utils import timezone
from rest_framework import status

from apps.responses.models import Response, QuestionnaireProgress


# ============================================================================
# Model Tests
# ============================================================================

@pytest.mark.django_db
class TestResponseModel:
    """Test cases for the Response model."""

    def test_create_response(self, user, question, layer, option):
        """Test creating a response."""
        response = Response.objects.create(
            user=user,
            question=question,
            layer=layer,
            selected_option_ids=[option.id]
        )

        assert response.user == user
        assert response.question == question
        assert response.layer == layer
        assert option.id in response.selected_option_ids

    def test_response_str_representation(self, response_obj):
        """Test response string representation."""
        assert response_obj.user.email in str(response_obj)
        assert response_obj.question.id in str(response_obj)

    def test_response_multi_select(self, user, question, layer, create_option):
        """Test response with multiple selections."""
        opt1 = create_option(option_number=1)
        opt2 = create_option(option_number=2)

        response = Response.objects.create(
            user=user,
            question=question,
            layer=layer,
            selected_option_ids=[opt1.id, opt2.id]
        )

        assert len(response.selected_option_ids) == 2
        assert opt1.id in response.selected_option_ids
        assert opt2.id in response.selected_option_ids

    def test_mark_completed(self, response_obj):
        """Test marking response as completed."""
        assert response_obj.completed_at is None

        response_obj.mark_completed()

        assert response_obj.completed_at is not None

    def test_response_unique_constraint(self, user, question, layer, option):
        """Test unique constraint on user + question + layer."""
        Response.objects.create(
            user=user,
            question=question,
            layer=layer,
            selected_option_ids=[option.id]
        )

        with pytest.raises(Exception):  # IntegrityError
            Response.objects.create(
                user=user,
                question=question,
                layer=layer,
                selected_option_ids=[option.id]
            )


@pytest.mark.django_db
class TestQuestionnaireProgressModel:
    """Test cases for the QuestionnaireProgress model."""

    def test_create_progress(self, user, question):
        """Test creating questionnaire progress."""
        progress = QuestionnaireProgress.objects.create(
            user=user,
            question=question,
            current_phase='q1_selection',
            current_layer=1
        )

        assert progress.user == user
        assert progress.question == question
        assert progress.current_layer == 1
        assert not progress.is_completed

    def test_progress_str_representation(self, user, question):
        """Test progress string representation."""
        progress = QuestionnaireProgress.objects.create(
            user=user,
            question=question,
            current_phase='q1_review',
            current_layer=2
        )

        assert user.email in str(progress)
        assert question.id in str(progress)

    def test_mark_completed(self, user, question):
        """Test marking progress as completed."""
        progress = QuestionnaireProgress.objects.create(
            user=user,
            question=question,
            current_phase='q1_selection',
            current_layer=3
        )

        assert not progress.is_completed
        assert progress.completed_at is None

        progress.mark_completed()

        assert progress.is_completed
        assert progress.completed_at is not None

    def test_progress_unique_constraint(self, user, question):
        """Test unique constraint on user + question."""
        QuestionnaireProgress.objects.create(
            user=user,
            question=question,
            current_phase='q1_selection',
            current_layer=1
        )

        with pytest.raises(Exception):  # IntegrityError
            QuestionnaireProgress.objects.create(
                user=user,
                question=question,
                current_phase='q2_review',
                current_layer=2
            )


# ============================================================================
# Response API Tests
# ============================================================================

@pytest.mark.django_db
class TestResponseAPI:
    """Test cases for Response API endpoints."""

    def test_list_responses(self, authenticated_client, response_obj):
        """Test listing user's responses."""
        response = authenticated_client.get('/api/v1/user/responses/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1

    def test_list_responses_unauthenticated(self, api_client):
        """Test responses list requires authentication."""
        response = api_client.get('/api/v1/user/responses/')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_response(self, authenticated_client, question, layer, option):
        """Test creating a new response."""
        response = authenticated_client.post('/api/v1/user/responses/', {
            'question': question.id,
            'layer': str(layer.id),
            'selected_option_ids': [str(option.id)]
        })

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['question'] == question.id

    def test_get_response_detail(self, authenticated_client, response_obj):
        """Test getting response details."""
        response = authenticated_client.get(f'/api/v1/user/responses/{response_obj.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert str(response.data['id']) == str(response_obj.id)

    def test_update_response(self, authenticated_client, response_obj, create_option):
        """Test updating a response."""
        new_option = create_option(option_number=99)

        response = authenticated_client.patch(f'/api/v1/user/responses/{response_obj.id}/', {
            'selected_option_ids': [str(new_option.id)]
        })

        assert response.status_code == status.HTTP_200_OK
        response_obj.refresh_from_db()
        assert new_option.id in response_obj.selected_option_ids

    def test_delete_response(self, authenticated_client, response_obj):
        """Test deleting a response."""
        response_id = response_obj.id
        response = authenticated_client.delete(f'/api/v1/user/responses/{response_id}/')

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Response.objects.filter(id=response_id).exists()

    def test_get_responses_by_question(self, authenticated_client, response_obj, question):
        """Test getting responses by question."""
        response = authenticated_client.get(
            f'/api/v1/user/responses/by-question/{question.id}/'
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    def test_responses_are_user_specific(self, api_client, response_obj, create_user):
        """Test that responses are scoped to authenticated user."""
        # Create another user and authenticate as them
        other_user = create_user(email='other@example.com')

        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(other_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        # Other user should not see first user's responses
        response = api_client.get('/api/v1/user/responses/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 0


# ============================================================================
# Response Summary API Tests
# ============================================================================

@pytest.mark.django_db
class TestResponseSummaryAPI:
    """Test cases for response summary endpoint."""

    def test_get_response_summary(self, authenticated_client, response_obj):
        """Test getting response summary."""
        response = authenticated_client.get('/api/v1/user/responses/summary/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    def test_summary_includes_completion_status(
        self, authenticated_client, user, question, layer, option
    ):
        """Test summary includes completion status."""
        # Create a completed response
        Response.objects.create(
            user=user,
            question=question,
            layer=layer,
            selected_option_ids=[option.id],
            completed_at=timezone.now()
        )

        response = authenticated_client.get('/api/v1/user/responses/summary/')

        assert response.status_code == status.HTTP_200_OK
        summary = response.data[0]
        assert 'completed_layers' in summary
        assert 'total_layers' in summary
        assert 'is_completed' in summary


# ============================================================================
# Bulk Save API Tests
# ============================================================================

@pytest.mark.django_db
class TestBulkSaveAPI:
    """Test cases for bulk save endpoint."""

    def test_bulk_save_responses(
        self, authenticated_client, question, layer, option, create_layer, create_option
    ):
        """Test bulk saving multiple responses."""
        layer2 = create_layer(layer_number=2)
        option2 = create_option(layer_ref=layer2, option_number=2)

        response = authenticated_client.post('/api/v1/user/responses/bulk_save/', {
            'responses': [
                {
                    'question': question.id,
                    'layer': str(layer.id),
                    'selected_option_ids': [str(option.id)]
                },
                {
                    'question': question.id,
                    'layer': str(layer2.id),
                    'selected_option_ids': [str(option2.id)]
                }
            ]
        }, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['created'] == 2
        assert response.data['failed'] == 0

    def test_bulk_save_empty_responses(self, authenticated_client):
        """Test bulk save with empty responses."""
        response = authenticated_client.post('/api/v1/user/responses/bulk_save/', {
            'responses': []
        }, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_bulk_save_partial_failure(
        self, authenticated_client, question, layer, option
    ):
        """Test bulk save with some invalid responses."""
        response = authenticated_client.post('/api/v1/user/responses/bulk_save/', {
            'responses': [
                {
                    'question': question.id,
                    'layer': str(layer.id),
                    'selected_option_ids': [str(option.id)]
                },
                {
                    # Invalid - missing required fields
                    'question': 'invalid-id'
                }
            ]
        }, format='json')

        # Should still create the valid one
        assert response.data['created'] >= 1 or response.data['failed'] >= 1


# ============================================================================
# Questionnaire Progress API Tests
# ============================================================================

@pytest.mark.django_db
class TestQuestionnaireProgressAPI:
    """Test cases for QuestionnaireProgress API endpoints."""

    def test_list_progress(self, authenticated_client, user, question):
        """Test listing questionnaire progress."""
        QuestionnaireProgress.objects.create(
            user=user,
            question=question,
            current_phase='q1_selection',
            current_layer=1
        )

        response = authenticated_client.get('/api/v1/user/progress/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1

    def test_list_progress_unauthenticated(self, api_client):
        """Test progress list requires authentication."""
        response = api_client.get('/api/v1/user/progress/')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_progress(self, authenticated_client, question):
        """Test creating questionnaire progress."""
        response = authenticated_client.post('/api/v1/user/progress/', {
            'question': question.id,
            'current_phase': 'q1_selection',
            'current_layer': 1
        })

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['current_layer'] == 1

    def test_update_progress(self, authenticated_client, user, question):
        """Test updating questionnaire progress."""
        progress = QuestionnaireProgress.objects.create(
            user=user,
            question=question,
            current_phase='q1_selection',
            current_layer=1
        )

        response = authenticated_client.patch(f'/api/v1/user/progress/{progress.id}/', {
            'current_phase': 'q2_review',
            'current_layer': 2
        })

        assert response.status_code == status.HTTP_200_OK
        progress.refresh_from_db()
        assert progress.current_layer == 2

    def test_get_progress_by_question(self, authenticated_client, user, question):
        """Test getting progress by question."""
        QuestionnaireProgress.objects.create(
            user=user,
            question=question,
            current_phase='q1_selection',
            current_layer=1
        )

        response = authenticated_client.get(
            f'/api/v1/user/progress/by-question/{question.id}/'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['question'] == question.id

    def test_get_progress_by_question_not_found(self, authenticated_client, question):
        """Test getting progress for question with no progress."""
        response = authenticated_client.get(
            f'/api/v1/user/progress/by-question/{question.id}/'
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_progress_is_user_specific(self, api_client, user, question, create_user):
        """Test that progress is scoped to authenticated user."""
        # Create progress for first user
        QuestionnaireProgress.objects.create(
            user=user,
            question=question,
            current_phase='q1_selection',
            current_layer=1
        )

        # Authenticate as different user
        other_user = create_user(email='other@example.com')
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(other_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        # Other user should not see first user's progress
        response = api_client.get('/api/v1/user/progress/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 0


# ============================================================================
# Response Flow Integration Tests
# ============================================================================

@pytest.mark.django_db
class TestResponseFlowIntegration:
    """Integration tests for the complete response flow."""

    def test_complete_question_flow(
        self, authenticated_client, question, create_layer, create_option
    ):
        """Test completing a full 3-layer question flow."""
        # Create 3 layers with options
        layers = []
        options = []
        for i in range(1, 4):
            layer = create_layer(question_ref=question, layer_number=i)
            opt = create_option(
                question_ref=question,
                layer_ref=layer,
                option_number=i
            )
            layers.append(layer)
            options.append(opt)

        # Create progress
        progress_response = authenticated_client.post('/api/v1/user/progress/', {
            'question': question.id,
            'current_phase': 'q1_selection',
            'current_layer': 1
        })
        assert progress_response.status_code == status.HTTP_201_CREATED
        progress_id = progress_response.data['id']

        # Submit responses for each layer
        for i, (layer, opt) in enumerate(zip(layers, options)):
            resp = authenticated_client.post('/api/v1/user/responses/', {
                'question': question.id,
                'layer': str(layer.id),
                'selected_option_ids': [str(opt.id)]
            })
            assert resp.status_code == status.HTTP_201_CREATED

            # Update progress
            authenticated_client.patch(f'/api/v1/user/progress/{progress_id}/', {
                'current_layer': i + 2 if i < 2 else 3,
                'current_phase': f'q{i+2}_selection' if i < 2 else 'completed'
            })

        # Verify summary shows completion
        summary = authenticated_client.get('/api/v1/user/responses/summary/')
        assert summary.status_code == status.HTTP_200_OK

        question_summary = next(
            (s for s in summary.data if s['question_id'] == question.id),
            None
        )
        assert question_summary is not None
        assert question_summary['completed_layers'] == 3
