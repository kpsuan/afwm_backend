# AWFM Backend

**A Whole Family Matter** - Interdependent Care Planning (ICP) Platform

Django backend following the [HackSoft Django Styleguide](https://github.com/HackSoftware/Django-Styleguide).

## Quick Start

```bash
# Activate virtual environment
source ../env/bin/activate

# Run migrations (first time)
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

## Project Structure

```
afwm_backend/
├── config/               # Django configuration
│   ├── settings/
│   │   ├── base.py      # Shared settings
│   │   ├── local.py     # Development (default)
│   │   └── production.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── apps/                 # All Django apps
│   ├── accounts/        # User model, authentication
│   ├── teams/           # Teams, memberships, witness role
│   ├── content/         # Questions, checkpoints, options
│   ├── responses/       # User responses, recordings
│   ├── communication/   # Channels, messages, notifications
│   └── core/            # Supporting features
│
├── common/              # Shared utilities
│   ├── models.py        # BaseModel, SoftDeleteModel
│   ├── exceptions.py    # Custom exceptions
│   └── utils.py         # Helper functions
│
└── manage.py
```

## Settings

- **Development**: Uses `config.settings.local` (default)
- **Production**: Uses `config.settings.production`

Change settings:
```bash
export DJANGO_SETTINGS_MODULE=config.settings.production
```

## Documentation

All documentation is in `/Documentation Lean MVP/`:

- [DATABASE_SCHEMA.md](../Documentation%20Lean%20MVP/DATABASE_SCHEMA.md) - Complete database schema
- [SCHEMA_SUMMARY.md](../Documentation%20Lean%20MVP/SCHEMA_SUMMARY.md) - Quick reference
- [REORGANIZATION_COMPLETE.md](../Documentation%20Lean%20MVP/REORGANIZATION_COMPLETE.md) - Structure changes
- [REMAINING_MODELS_REFERENCE.md](../Documentation%20Lean%20MVP/REMAINING_MODELS_REFERENCE.md) - Models to implement

## Pre-MVP Scope

- **4 Questions**: Q10A, Q10B, Q11, Q12
- **Checkpoint Flow**: CP1, CP2, CP3 per question
- **Key Features**: HCW attestation, Witness role, Leader defaults

## Tech Stack

- **Django 6.0**
- **PostgreSQL** (required for ArrayField, JSONField)
- **Python 3.12**

---

**Status**: Week 3 - Models implemented, ready for API development
