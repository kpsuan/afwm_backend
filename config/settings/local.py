"""
Django settings for AWFM Backend - Local Development

Use this for local development on your machine.
"""

from .base import *  # noqa
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(BASE_DIR / '.env')

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-w(32%7g)uupkyq^og9*1qxjr0^r+og8tv2hs(v1d--4-1tox!n'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]']
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

# PostgreSQL (Required for ArrayField, JSONField)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'awfm_db',
        'USER': 'awfm_user',
        'PASSWORD': 'awfm_password_2026',
        'HOST': 'localhost',
        'PORT': '5432',
        'OPTIONS': {
            'options': '-c search_path=public'
        },
    }
}

# For initial development without PostgreSQL, you can use SQLite:
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }


# Development-specific settings

# Show detailed error pages
DEBUG_PROPAGATE_EXCEPTIONS = True

# Django Debug Toolbar (install with: pip install django-debug-toolbar)
# Uncomment when you install it:
# INSTALLED_APPS += ['debug_toolbar']
# MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
# INTERNAL_IPS = ['127.0.0.1']

# Email backend for development - Using SendGrid
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.sendgrid.net'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'apikey'  # This is literal 'apikey'
EMAIL_HOST_PASSWORD = os.getenv('SENDGRID_API_KEY')
DEFAULT_FROM_EMAIL = os.getenv('FROM_EMAIL', 'noreply@awfm.com')


# Cache (dummy cache for development)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps': {  # Our apps logging
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}


# CORS Headers (Development)
# Allow all origins for local development
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# For production, you'll want to restrict this in production.py:
# CORS_ALLOWED_ORIGINS = [
#     'https://yourdomain.com',
#     'https://www.yourdomain.com',
# ]


# Cloudinary (for media storage - images, videos, recordings)
# Get credentials from .env file
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.getenv('CLOUDINARY_CLOUD_NAME'),
    'API_KEY': os.getenv('CLOUDINARY_API_KEY'),
    'API_SECRET': os.getenv('CLOUDINARY_API_SECRET'),
}

# Only enable Cloudinary storage if credentials are configured
if CLOUDINARY_STORAGE.get('CLOUD_NAME'):
    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
