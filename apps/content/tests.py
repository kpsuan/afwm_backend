"""
AWFM Content App - Test Cases

Comprehensive tests for content models (Questions, Layers, Options, Components, PPR).
"""

import pytest
from django.utils import timezone
from rest_framework import status

from apps.content.models import (
    Question,
    Layer,
    Option,
    Component,
    PersonalPatternRecognition
)


# ============================================================================
# Model Tests
# ============================================================================

@pytest.mark.django_db
class TestQuestionModel:
    """Test cases for the Question model."""

    def test_create_question(self):
        """Test creating a question."""
        question = Question.objects.create(
            id='Q10A',
            title='Test Question',
            question_text='What is your test preference?',
            display_order=1,
            batch_number=1,
            category='UHCDA Priority Values'
        )

        assert question.id == 'Q10A'
        assert question.title == 'Test Question'
        assert question.is_active

    def test_question_str_representation(self, question):
        """Test question string representation."""
        assert question.id in str(question)
        assert question.title in str(question)

    def test_question_ordering(self, create_question):
        """Test questions are ordered by display_order."""
        q1 = create_question(id='Q1', display_order=2)
        q2 = create_question(id='Q2', display_order=1)
        q3 = create_question(id='Q3', display_order=3)

        questions = list(Question.objects.all().order_by('display_order'))
        assert questions[0] == q2
        assert questions[1] == q1
        assert questions[2] == q3


@pytest.mark.django_db
class TestLayerModel:
    """Test cases for the Layer model."""

    def test_create_layer(self, question):
        """Test creating a layer."""
        layer = Layer.objects.create(
            question=question,
            layer_number=1,
            layer_title='YOUR POSITION',
            layer_question='What is your position?',
            selection_type='single',
            components_at_selection=['C1', 'C3'],
            components_at_confirmation=['C2', 'C4']
        )

        assert layer.question == question
        assert layer.layer_number == 1
        assert layer.selection_type == 'single'

    def test_layer_str_representation(self, layer):
        """Test layer string representation."""
        assert f'L{layer.layer_number}' in str(layer)
        assert layer.layer_title in str(layer)

    def test_layer_unique_constraint(self, question, create_layer):
        """Test unique constraint on question + layer_number."""
        create_layer(question_ref=question, layer_number=1)

        with pytest.raises(Exception):  # IntegrityError
            create_layer(question_ref=question, layer_number=1)


@pytest.mark.django_db
class TestOptionModel:
    """Test cases for the Option model."""

    def test_create_option(self, question, layer):
        """Test creating an option."""
        option = Option.objects.create(
            question=question,
            layer=layer,
            option_number=1,
            option_text='Option 1 text',
            display_order=1
        )

        assert option.question == question
        assert option.layer == layer
        assert option.option_number == 1

    def test_option_str_representation(self, option):
        """Test option string representation."""
        assert f'Option {option.option_number}' in str(option)


@pytest.mark.django_db
class TestComponentModel:
    """Test cases for the Component model."""

    def test_create_component(self, option):
        """Test creating a component."""
        component = Component.objects.create(
            option=option,
            component_type='C1',
            component_text='This is the form response option text.'
        )

        assert component.option == option
        assert component.component_type == 'C1'
        assert component.character_count == len(component.component_text)

    def test_component_auto_character_count(self, option):
        """Test automatic character count calculation."""
        text = 'Test component text with exactly 42 characters.'
        component = Component.objects.create(
            option=option,
            component_type='C2',
            component_text=text
        )

        assert component.character_count == len(text)

    def test_component_str_representation(self, component):
        """Test component string representation."""
        assert component.component_type in str(component)

    def test_component_types(self, option):
        """Test all component types can be created."""
        component_types = ['C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'C9', 'C10', 'C11']

        for i, ctype in enumerate(component_types):
            Component.objects.create(
                option=option,
                component_type=ctype,
                component_text=f'Component {ctype} text'
            )

        assert Component.objects.filter(option=option).count() == len(component_types)


@pytest.mark.django_db
class TestPPRModel:
    """Test cases for the PersonalPatternRecognition model."""

    def test_create_ppr(self, question):
        """Test creating a PPR pattern."""
        ppr = PersonalPatternRecognition.objects.create(
            question=question,
            pattern_name='Comfort-Focused with Quality of Life',
            l1_option=1,
            l2_options=[1, 2],
            l3_option=3,
            ppr_text='This is the PPR synthesis text for the pattern.'
        )

        assert ppr.question == question
        assert ppr.l1_option == 1
        assert ppr.l2_options == [1, 2]
        assert ppr.character_count == len(ppr.ppr_text)

    def test_ppr_str_representation(self, question):
        """Test PPR string representation."""
        ppr = PersonalPatternRecognition.objects.create(
            question=question,
            pattern_name='Test Pattern',
            l1_option=1,
            l2_options=[1],
            l3_option=1,
            ppr_text='Test text'
        )

        assert question.id in str(ppr)
        assert ppr.pattern_name in str(ppr)


# ============================================================================
# API Tests - Questions
# ============================================================================

@pytest.mark.django_db
class TestQuestionAPI:
    """Test cases for Question API endpoints."""

    def test_list_questions(self, api_client, question):
        """Test listing questions."""
        response = api_client.get('/api/v1/content/questions/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1

    def test_list_questions_is_public(self, api_client, question):
        """Test questions list is publicly accessible."""
        response = api_client.get('/api/v1/content/questions/')

        assert response.status_code == status.HTTP_200_OK

    def test_get_question_detail(self, api_client, question):
        """Test getting question details."""
        response = api_client.get(f'/api/v1/content/questions/{question.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == question.id
        assert response.data['title'] == question.title

    def test_get_question_with_layers(self, api_client, question, layer):
        """Test getting question with nested layers."""
        response = api_client.get(f'/api/v1/content/questions/{question.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert 'layers' in response.data
        assert len(response.data['layers']) >= 1

    def test_get_question_layers_action(self, api_client, question, layer):
        """Test getting layers via action endpoint."""
        response = api_client.get(f'/api/v1/content/questions/{question.id}/layers/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    def test_get_question_ppr_patterns(self, api_client, question):
        """Test getting PPR patterns for question."""
        PersonalPatternRecognition.objects.create(
            question=question,
            pattern_name='Test Pattern',
            l1_option=1,
            l2_options=[1],
            l3_option=1,
            ppr_text='Test PPR text'
        )

        response = api_client.get(f'/api/v1/content/questions/{question.id}/ppr-patterns/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    def test_filter_questions_by_batch(self, api_client, create_question):
        """Test filtering questions by batch number."""
        create_question(id='QBatch1', batch_number=1)
        create_question(id='QBatch2', batch_number=2)

        response = api_client.get('/api/v1/content/questions/?batch_number=1')

        assert response.status_code == status.HTTP_200_OK
        for q in response.data['results']:
            assert q['batch_number'] == 1


# ============================================================================
# API Tests - Layers
# ============================================================================

@pytest.mark.django_db
class TestLayerAPI:
    """Test cases for Layer API endpoints."""

    def test_list_layers(self, api_client, layer):
        """Test listing layers."""
        response = api_client.get('/api/v1/content/layers/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1

    def test_get_layer_detail(self, api_client, layer):
        """Test getting layer details."""
        response = api_client.get(f'/api/v1/content/layers/{layer.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['layer_number'] == layer.layer_number

    def test_filter_layers_by_selection_type(self, api_client, question, create_layer):
        """Test filtering layers by selection type."""
        create_layer(question_ref=question, layer_number=1, selection_type='single')
        create_layer(question_ref=question, layer_number=2, selection_type='multi')

        response = api_client.get('/api/v1/content/layers/?selection_type=single')

        assert response.status_code == status.HTTP_200_OK
        for layer in response.data['results']:
            assert layer['selection_type'] == 'single'


# ============================================================================
# API Tests - Options
# ============================================================================

@pytest.mark.django_db
class TestOptionAPI:
    """Test cases for Option API endpoints."""

    def test_list_options(self, api_client, option):
        """Test listing options."""
        response = api_client.get('/api/v1/content/options/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1

    def test_get_option_detail(self, api_client, option):
        """Test getting option details."""
        response = api_client.get(f'/api/v1/content/options/{option.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['option_number'] == option.option_number

    def test_option_includes_components(self, api_client, option, component):
        """Test option includes nested components."""
        response = api_client.get(f'/api/v1/content/options/{option.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert 'components' in response.data
        assert len(response.data['components']) >= 1


# ============================================================================
# API Tests - Components
# ============================================================================

@pytest.mark.django_db
class TestComponentAPI:
    """Test cases for Component API endpoints."""

    def test_list_components(self, api_client, component):
        """Test listing components."""
        response = api_client.get('/api/v1/content/components/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1

    def test_get_component_detail(self, api_client, component):
        """Test getting component details."""
        response = api_client.get(f'/api/v1/content/components/{component.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['component_type'] == component.component_type

    def test_filter_components_by_type(self, api_client, option, create_component):
        """Test filtering components by type."""
        create_component(option_ref=option, component_type='C1')
        create_component(option_ref=option, component_type='C2')

        response = api_client.get('/api/v1/content/components/?component_type=C1')

        assert response.status_code == status.HTTP_200_OK
        for comp in response.data['results']:
            assert comp['component_type'] == 'C1'


# ============================================================================
# API Tests - PPR
# ============================================================================

@pytest.mark.django_db
class TestPPRAPI:
    """Test cases for PPR API endpoints."""

    def test_list_ppr_patterns(self, api_client, question):
        """Test listing PPR patterns."""
        PersonalPatternRecognition.objects.create(
            question=question,
            pattern_name='Pattern 1',
            l1_option=1,
            l2_options=[1],
            l3_option=1,
            ppr_text='PPR text 1'
        )

        response = api_client.get('/api/v1/content/ppr/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1

    def test_get_ppr_detail(self, api_client, question):
        """Test getting PPR details."""
        ppr = PersonalPatternRecognition.objects.create(
            question=question,
            pattern_name='Test Pattern',
            l1_option=1,
            l2_options=[1, 2],
            l3_option=3,
            ppr_text='Test PPR text for pattern'
        )

        response = api_client.get(f'/api/v1/content/ppr/{ppr.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['pattern_name'] == 'Test Pattern'
        assert response.data['l2_options'] == [1, 2]


# ============================================================================
# Content Hierarchy Tests
# ============================================================================

@pytest.mark.django_db
class TestContentHierarchy:
    """Test cases for content hierarchy relationships."""

    def test_question_layer_relationship(self, question, create_layer):
        """Test question has multiple layers."""
        l1 = create_layer(question_ref=question, layer_number=1)
        l2 = create_layer(question_ref=question, layer_number=2)
        l3 = create_layer(question_ref=question, layer_number=3)

        assert question.layers.count() == 3
        assert l1 in question.layers.all()
        assert l2 in question.layers.all()
        assert l3 in question.layers.all()

    def test_layer_option_relationship(self, question, layer, create_option):
        """Test layer has multiple options."""
        for i in range(1, 5):
            create_option(
                question_ref=question,
                layer_ref=layer,
                option_number=i,
                display_order=i
            )

        assert layer.options.count() == 4

    def test_option_component_relationship(self, option, create_component):
        """Test option has multiple components."""
        for ctype in ['C1', 'C2', 'C3']:
            create_component(option_ref=option, component_type=ctype)

        assert option.components.count() == 3

    def test_full_content_hierarchy(self, create_question, create_layer, create_option, create_component):
        """Test full content hierarchy from question to component."""
        question = create_question(id='QFull')
        layer = create_layer(question_ref=question, layer_number=1)
        option = create_option(question_ref=question, layer_ref=layer, option_number=1)
        component = create_component(option_ref=option, component_type='C1')

        # Navigate from component up to question
        assert component.option == option
        assert component.option.layer == layer
        assert component.option.question == question
