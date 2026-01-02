"""
Django settings for AWFM Backend project - Base Settings

AWFM: A Whole Family Matter
Interdependent Care Planning (ICP) Platform

Pre-MVP: January - March 2026
- 4 Questions: Q10A, Q10B, Q11, Q12
- Checkpoint Flow Architecture (Variation 5)
- HCW Attestation, Witness Role, Leader Defaults

These settings are common to all environments.
Override in local.py or production.py as needed.
"""

from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
# BASE_DIR is now two levels up: config/settings/base.py → afwm_backend/
BASE_DIR = Path(__file__).resolve().parent.parent.parent


# CRITICAL: Custom User Model
# Must be set BEFORE first migration!
AUTH_USER_MODEL = 'accounts.User'


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.postgres',


    # Third-party apps
    'channels',  # WebSocket support
    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework_simplejwt',
    'corsheaders',
    'drf_spectacular',  # OpenAPI/Swagger documentation
    'social_django',  # Social authentication (Google OAuth)
    'cloudinary',  # Cloudinary SDK
    'cloudinary_storage',  # Django Cloudinary storage

    # AWFM Apps (in apps/ folder)
    'apps.accounts.apps.AccountsConfig',
    'apps.teams.apps.TeamsConfig',
    'apps.content.apps.ContentConfig',
    'apps.responses.apps.ResponsesConfig',
    'apps.communication.apps.CommunicationConfig',  # WebSocket notifications
    # Add these after implementing their models:
    # 'apps.core.apps.CoreConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # CORS - must be before CommonMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'social_django.context_processors.backends',
                'social_django.context_processors.login_redirect',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Password hashers
# https://docs.djangoproject.com/en/6.0/topics/auth/passwords/
# BCrypt is more secure than PBKDF2 for password hashing
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',  # Primary hasher
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',  # Fallback for existing passwords
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files (user uploads)
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'


# Default primary key field type
# https://docs.djangoproject.com/en/6.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Django REST Framework
# https://www.django-rest-framework.org/api-guide/settings/

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',  # Allow unauthenticated access by default
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ],
    'EXCEPTION_HANDLER': 'rest_framework.views.exception_handler',
    'DATETIME_FORMAT': '%Y-%m-%dT%H:%M:%S.%fZ',
    'DATETIME_INPUT_FORMATS': ['%Y-%m-%dT%H:%M:%S.%fZ', 'iso-8601'],
}


# DRF Spectacular (OpenAPI/Swagger)
# https://drf-spectacular.readthedocs.io/

SPECTACULAR_SETTINGS = {
    'TITLE': 'AWFM API',
    'DESCRIPTION': 'A Whole Family Matter - Interdependent Care Planning Platform API',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SCHEMA_PATH_PREFIX': '/api/v1/',
}


# Simple JWT Settings
# https://django-rest-framework-simplejwt.readthedocs.io/

from datetime import timedelta

# Note: SIMPLE_JWT will use Django's SECRET_KEY by default if SIGNING_KEY is not set
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),  # Access token valid for 60 minutes
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),  # Refresh token valid for 7 days
    'ROTATE_REFRESH_TOKENS': True,  # Rotate refresh tokens on use
    'BLACKLIST_AFTER_ROTATION': False,  # Don't require blacklist app for now
    'UPDATE_LAST_LOGIN': True,  # Update last_login field on login

    'ALGORITHM': 'HS256',
    # SIGNING_KEY defaults to Django SECRET_KEY if not set

    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',

    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',

    'JTI_CLAIM': 'jti',
}


# Email Settings
# SendGrid configuration (API key set in environment)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.sendgrid.net'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'apikey'  # This is literal string 'apikey' for SendGrid
# EMAIL_HOST_PASSWORD should be set in environment variables (local.py or production.py)

# Default from email
DEFAULT_FROM_EMAIL = 'noreply@awfm.com'  # Override in environment settings

# CORS Headers
# https://github.com/adamchainz/django-cors-headers

# CORS will be configured per environment (local.py, production.py)


# Django Channels (WebSocket support)
# https://channels.readthedocs.io/

ASGI_APPLICATION = 'config.asgi.application'

# Channel Layers - Redis backend for WebSocket message broker
# REDIS_URL must be set in environment variables
import os

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0')],
        },
    },
}


# Authentication Backends
# https://python-social-auth.readthedocs.io/

AUTHENTICATION_BACKENDS = [
    'social_core.backends.google.GoogleOAuth2',  # Google OAuth2
    'django.contrib.auth.backends.ModelBackend',  # Default Django backend
]


# Social Auth Settings
# https://python-social-auth.readthedocs.io/en/latest/configuration/settings.html

# Google OAuth2 - credentials set in local.py/production.py via environment variables
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.environ.get('GOOGLE_OAUTH2_CLIENT_ID', '')
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.environ.get('GOOGLE_OAUTH2_CLIENT_SECRET', '')

# Request additional user info from Google
SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
]

# Extra data to save from Google profile
SOCIAL_AUTH_GOOGLE_OAUTH2_EXTRA_DATA = [
    ('picture', 'profile_photo_url'),
    ('given_name', 'first_name'),
    ('family_name', 'last_name'),
]

# Social auth pipeline - customize user creation
SOCIAL_AUTH_PIPELINE = (
    'social_core.pipeline.social_auth.social_details',
    'social_core.pipeline.social_auth.social_uid',
    'social_core.pipeline.social_auth.auth_allowed',
    'social_core.pipeline.social_auth.social_user',
    'social_core.pipeline.user.get_username',
    'apps.accounts.pipeline.create_user',  # Custom user creation
    'social_core.pipeline.social_auth.associate_user',
    'social_core.pipeline.social_auth.load_extra_data',
    'apps.accounts.pipeline.save_profile',  # Save extra profile data
)

# Social auth settings
SOCIAL_AUTH_USERNAME_IS_FULL_EMAIL = True
SOCIAL_AUTH_SANITIZE_REDIRECTS = True
SOCIAL_AUTH_REDIRECT_IS_HTTPS = False  # Set to True in production

# Where to redirect after login
SOCIAL_AUTH_LOGIN_REDIRECT_URL = '/'
SOCIAL_AUTH_LOGIN_ERROR_URL = '/login?error=oauth'
