"""
Django settings for AWFM Backend - Testing

Use this for running pytest tests.
"""

from .base import *  # noqa
import os

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-test-key-only-for-testing'

DEBUG = False

ALLOWED_HOSTS = ['*']
FRONTEND_URL = 'http://localhost:3000'

# Use SQLite for testing (faster and doesn't require PostgreSQL permissions)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Speed up password hashing for tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable email sending during tests
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Disable caching during tests
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# Disable logging during tests
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'root': {
        'handlers': ['null'],
        'level': 'CRITICAL',
    },
}

# CORS
CORS_ALLOW_ALL_ORIGINS = True

# Cloudinary - disabled for testing
CLOUDINARY_STORAGE = {}

# Django REST Framework - throttle rates disabled for testing
REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # noqa F405
    'DEFAULT_THROTTLE_RATES': {},
}

# Celery - use synchronous mode for testing
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
