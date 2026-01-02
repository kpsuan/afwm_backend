"""
Django management command to seed AWFM question content from markdown files.

Usage:
    python manage.py seed_content
    python manage.py seed_content --question Q10A
    python manage.py seed_content --clear  # Clear existing data first
"""

import os
import re
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.content.models import (
    Question,
    Layer,
    Option,
    Component,
    PersonalPatternRecognition
)


class Command(BaseCommand):
    help = 'Seed AWFM question content from markdown files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--question',
            type=str,
            help='Seed specific question (e.g., Q10A, Q10B, Q11, Q12)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing content before seeding'
        )

    def handle(self, *args, **options):
        """Main command handler."""

        if options['clear']:
            self.stdout.write(self.style.WARNING('Clearing existing content...'))
            self.clear_content()

        # Get question files
        question_files = self.get_question_files(options.get('question'))

        if not question_files:
            self.stdout.write(self.style.ERROR('No question files found!'))
            return

        # Seed each question
        for question_file in question_files:
            self.seed_question(question_file)

        self.stdout.write(self.style.SUCCESS('\n✅ Seeding complete!'))

    def clear_content(self):
        """Clear all existing content."""
        PersonalPatternRecognition.objects.all().delete()
        Component.objects.all().delete()
        Option.objects.all().delete()
        Layer.objects.all().delete()
        Question.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('✓ Content cleared'))

    def get_question_files(self, specific_question=None):
        """Get list of question markdown files to process."""
        # Path to Documentation Lean MVP folder
        docs_path = Path('/home/pran/awfm/Documentation Lean MVP')

        if specific_question:
            # Seed specific question
            pattern = f'{specific_question}-FINAL-CONTENT-*.md'
        else:
            # Seed all questions (Q10A, Q10B, Q11, Q12)
            pattern = 'Q1*-FINAL-CONTENT-*.md'

        files = sorted(docs_path.glob(pattern))
        return files

    @transaction.atomic
    def seed_question(self, file_path):
        """Parse and seed a single question file."""
        self.stdout.write(f'\n📄 Processing {file_path.name}...')

        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract question ID from filename (e.g., Q10A from Q10A-FINAL-CONTENT-V5-122425.md)
        question_id = re.match(r'(Q\d+[A-Z]?)', file_path.name).group(1)

        # Parse question metadata
        question_data = self.parse_question_metadata(content, question_id)

        # Create Question
        question = Question.objects.create(**question_data)
        self.stdout.write(self.style.SUCCESS(f'  ✓ Created Question: {question.id}'))

        # Parse and create layers, options, components
        self.parse_layers(content, question)

        # Parse and create PPR patterns
        self.parse_ppr_patterns(content, question)

    def parse_question_metadata(self, content, question_id):
        """Extract question metadata from markdown content."""
        # Extract question text from first checkpoint
        question_match = re.search(r'\*\*Question:\*\* (.+)', content)
        question_text = question_match.group(1) if question_match else ''

        # Determine question info based on ID
        question_info = {
            'Q10A': {
                'title': 'Physical limitations',
                'category': 'UHCDA Priority Values',
                'display_order': 1,
                'batch_number': 1,
                'uhcda_section': 'Section 11.B.2'
            },
            'Q10B': {
                'title': 'Cognitive limitations',
                'category': 'UHCDA Priority Values',
                'display_order': 2,
                'batch_number': 1,
                'uhcda_section': 'Section 11.B.2'
            },
            'Q11': {
                'title': 'Pain management',
                'category': 'UHCDA Priority Values',
                'display_order': 3,
                'batch_number': 1,
                'uhcda_section': 'Section 11.B.3'
            },
            'Q12': {
                'title': 'Life extension vs quality',
                'category': 'UHCDA Priority Values',
                'display_order': 4,
                'batch_number': 1,
                'uhcda_section': 'Section 11.B.4'
            }
        }

        info = question_info.get(question_id, {
            'title': question_id,
            'category': 'UHCDA Priority Values',
            'display_order': 1,
            'batch_number': 1,
        })

        return {
            'id': question_id,
            'title': info['title'],
            'question_text': question_text,
            'category': info['category'],
            'display_order': info['display_order'],
            'batch_number': info['batch_number'],
            'uhcda_section': info.get('uhcda_section', ''),
            'is_active': True
        }

    def parse_layers(self, content, question):
        """Parse layers, options, and components from markdown."""
        # Split content by layer sections (still marked as "Checkpoint" in markdown files)
        layer_sections = re.split(r'# Checkpoint \d+:', content)[1:]  # Skip first (metadata)

        for layer_num, layer_section in enumerate(layer_sections, 1):
            # Parse layer metadata
            layer_data = self.parse_layer_metadata(layer_section, layer_num)

            # Create Layer
            layer = Layer.objects.create(
                question=question,
                **layer_data
            )
            self.stdout.write(f'  ✓ Created Layer {layer_num}: {layer.layer_title}')

            # Parse options within this layer
            self.parse_options(layer_section, question, layer)

    def parse_layer_metadata(self, layer_section, layer_num):
        """Extract layer metadata."""
        # Extract layer title
        title_match = re.search(r'^(.+)\n', layer_section)
        title = title_match.group(1).strip() if title_match else f'Layer {layer_num}'

        # Extract layer question
        question_match = re.search(r'\*\*Question:\*\* (.+)', layer_section)
        layer_question = question_match.group(1) if question_match else ''

        # Extract selection type
        selection_match = re.search(r'\*\*Selection Type:\*\* (.+)', layer_section)
        selection_text = selection_match.group(1) if selection_match else 'Single-select'
        selection_type = 'multi' if 'Multi-select' in selection_text else 'single'

        # Extract max selections for multi-select
        max_selections = None
        if 'Multi-select' in selection_text:
            max_match = re.search(r'choose up to (\d+)', selection_text)
            max_selections = int(max_match.group(1)) if max_match else 2

        # Extract components at selection and confirmation
        components_selection = []
        components_confirmation = []

        comp_sel_match = re.search(r'\*\*Components at Selection:\*\* (.+)', layer_section)
        if comp_sel_match:
            components_selection = re.findall(r'C\d+', comp_sel_match.group(1))

        comp_conf_match = re.search(r'\*\*Components at Confirmation:\*\* (.+)', layer_section)
        if comp_conf_match:
            components_confirmation = re.findall(r'C\d+', comp_conf_match.group(1))

        return {
            'layer_number': layer_num,
            'layer_title': title,
            'layer_question': layer_question,
            'selection_type': selection_type,
            'max_selections': max_selections,
            'components_at_selection': components_selection,
            'components_at_confirmation': components_confirmation
        }

    def parse_options(self, layer_section, question, layer):
        """Parse options and their components within a layer."""
        # Find all option sections
        option_sections = re.split(r'## OPTION (\d+):', layer_section)[1:]  # Skip first (metadata)

        # Process pairs of (option_number, option_content)
        for i in range(0, len(option_sections), 2):
            option_number = int(option_sections[i])
            option_content = option_sections[i + 1]

            # Extract option text (first line after the option number)
            option_text_match = re.search(r'^(.+)\n', option_content)
            option_text = option_text_match.group(1).strip() if option_text_match else f'Option {option_number}'

            # Create Option
            option = Option.objects.create(
                question=question,
                layer=layer,
                option_number=option_number,
                option_text=option_text,
                display_order=option_number
            )
            self.stdout.write(f'    ✓ Created Option {option_number}: {option_text[:50]}...')

            # Parse components within this option
            self.parse_components(option_content, option)

    def parse_components(self, option_content, option):
        """Parse components (C1-C11) within an option."""
        # Find all component sections
        component_pattern = r'### (C\d+): (.+?) \(\d+/\d+\)\n(.+?)(?=\n### C\d+:|$)'
        components = re.findall(component_pattern, option_content, re.DOTALL)

        for comp_type, comp_name, comp_text in components:
            # Clean up component text
            comp_text = comp_text.strip()

            # Create Component
            Component.objects.create(
                option=option,
                component_type=comp_type,
                component_text=comp_text
            )

    def parse_ppr_patterns(self, content, question):
        """Parse Personal Pattern Recognition patterns."""
        # Find PPR section
        ppr_match = re.search(r'# PERSONAL PATTERN RECOGNITION EXAMPLES(.+?)(?=# USER DECISION|# TEAM VISIBILITY|# CONTENT SUMMARY|$)', content, re.DOTALL)

        if not ppr_match:
            self.stdout.write(self.style.WARNING('  ⚠ No PPR patterns found'))
            return

        ppr_section = ppr_match.group(1)

        # Find all pattern sections
        pattern_sections = re.split(r'## PATTERN \d+:', ppr_section)[1:]  # Skip first (metadata)

        for pattern_content in pattern_sections:
            # Extract pattern name
            name_match = re.search(r'^(.+)\n', pattern_content)
            pattern_name = name_match.group(1).strip() if name_match else 'Unnamed Pattern'

            # Extract selection combination
            cp1_match = re.search(r'- CP1: .+ \(Option (\d+)\)|CP1: (.+)', pattern_content)
            cp2_match = re.search(r'- CP2: .+ \(Options? ([\d, ]+)\)|CP2: (.+)', pattern_content)
            cp3_match = re.search(r'- CP3: .+ \(Option (\d+)\)|CP3: (.+)', pattern_content)

            # Extract option numbers (L1, L2, L3 - still marked as CP in markdown files)
            l1_option = self.extract_option_number(pattern_content, 'CP1')
            l2_options = self.extract_option_numbers(pattern_content, 'CP2')
            l3_option = self.extract_option_number(pattern_content, 'CP3')

            # Extract PPR text
            ppr_text_match = re.search(r'\*\*PPR Text.+?:\*\* (.+)', pattern_content, re.DOTALL)
            ppr_text = ppr_text_match.group(1).strip() if ppr_text_match else ''

            # Remove character count and metadata from PPR text
            ppr_text = re.sub(r' \(\d+ chars\)', '', ppr_text)

            # Create PPR
            PersonalPatternRecognition.objects.create(
                question=question,
                pattern_name=pattern_name,
                l1_option=l1_option,
                l2_options=l2_options,
                l3_option=l3_option,
                ppr_text=ppr_text
            )
            self.stdout.write(f'  ✓ Created PPR: {pattern_name}')

    def extract_option_number(self, pattern_content, cp_label):
        """Extract single option number for CP1 or CP3."""
        # Look for the actual option text and map to option number
        option_map = {
            'Q10A': {
                'CP1': {
                    'Life extension is very important': 1,
                    'Staying alive somewhat important': 2,
                    'Avoid aggressive intervention': 3
                },
                'CP3': {
                    'Meeting people with disabilities': 8,
                    "Having my team's support": 9,
                    'Learning more about': 10,
                    'Understanding disability': 11
                }
            }
        }

        # Try to find option text in pattern content
        cp_match = re.search(rf'- {cp_label}: (.+)', pattern_content)
        if cp_match:
            option_text = cp_match.group(1).strip()
            # Try to match against known options
            # For now, extract from default numbering based on position
            if 'Life extension' in option_text or 'regardless of function' in option_text:
                return 1
            elif 'somewhat important' in option_text or 'depends on situation' in option_text:
                return 2
            elif 'Avoid aggressive' in option_text or 'function has declined' in option_text or 'function seriously declined' in option_text:
                return 3
            elif 'Meeting people' in option_text or 'disabilities living meaningful' in option_text:
                return 8
            elif 'team' in option_text.lower() and 'support' in option_text.lower() and 'advocacy' in option_text.lower():
                return 9
            elif 'Learning more' in option_text or 'interventions and their outcomes' in option_text or 'interventions and outcomes' in option_text:
                return 10
            elif 'Understanding disability' in option_text or "doesn't mean low quality" in option_text:
                return 11

        return 1  # Default

    def extract_option_numbers(self, pattern_content, cp_label):
        """Extract multiple option numbers for CP2 (multi-select)."""
        # Try to find option text in pattern content
        cp_match = re.search(rf'- {cp_label}: (.+)', pattern_content)
        if cp_match:
            option_text = cp_match.group(1).strip()

            # Map option text to numbers
            options = []
            if 'Worried doctors might undervalue' in option_text or 'undervalue my life' in option_text:
                options.append(4)
            if 'Uncertain what life' in option_text or 'physical limitations is like' in option_text:
                options.append(5)
            if 'Worried about becoming a burden' in option_text or 'burden to loved ones' in option_text:
                options.append(6)
            if 'Have seen others struggle' in option_text or 'struggle with physical limitations' in option_text:
                options.append(7)

            return options if options else [4]  # Default to first option

        return [4]  # Default
