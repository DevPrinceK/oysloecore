from pathlib import Path
import os
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Load environment variables from the project-local .env (kept out of git).
# This is explicit so it works regardless of the process working directory.
load_dotenv(dotenv_path=BASE_DIR / 'oysloecore' / '.env')


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "t", "yes", "y", "on"}


def _env_csv(name: str, default: list[str] | None = None) -> list[str]:
    value = os.getenv(name)
    if value is None:
        return default or []
    parts = [p.strip() for p in value.split(',')]
    return [p for p in parts if p]


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-change-me')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = _env_bool('DEBUG', default=True)

ALLOWED_HOSTS = _env_csv('ALLOWED_HOSTS', default=['*'])


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third party apps
    'channels',
    'corsheaders',
    'rest_framework',
    'knox',
    'drf_spectacular',
    'django_filters',

    # internal
    'accounts.apps.AccountsConfig',
    'apiv1.apps.Apiv1Config',
    'notifications.apps.NotificationsConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'oysloecore.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

ASGI_APPLICATION = 'oysloecore.asgi.application'
WSGI_APPLICATION = 'oysloecore.wsgi.application'


# channel layer config
environment = (os.getenv('ENVIRONMENT') or 'development').lower()

if environment == 'development':
    # Use in-memory channel layer for development
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    }
else:
    redis_host = os.getenv('REDIS_HOST', '127.0.0.1')
    try:
        redis_port = int(os.getenv('REDIS_PORT', '6379'))
    except ValueError:
        redis_port = 6379

    CHANNEL_LAYERS = {
        'default': {
            # Use 'channels_redis' for production
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                'hosts': [(redis_host, redis_port)],
            },
        },
    }



# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

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

# custom user model
AUTH_USER_MODEL = 'accounts.User'


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles/'

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

MEDIA_URL = '/assets/'
MEDIA_ROOT = BASE_DIR / "assets"

# Django REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'knox.auth.TokenAuthentication',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
}
# knox - make token non-expiry
REST_KNOX = {
    'TOKEN_TTL': None,
}

# django cors headers settings
CORS_ALLOW_ALL_ORIGINS = True

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Paystack configuration
PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY', '')
PAYSTACK_PUBLIC_KEY = os.getenv('PAYSTACK_PUBLIC_KEY', '')
PAYSTACK_BASE_URL = os.getenv('PAYSTACK_BASE_URL', 'https://api.paystack.co')

# Paystack Transfers (Mobile Money) bank_code mapping
#
# For Ghana MoMo, Paystack uses short codes like:
# - MTN: "mtn"
# - ATMoney & Airtel Money: "atl"
# - Vodafone: "vod"
#
# Keys are normalized (lowercased, alphanumeric only) to support common user inputs.
PAYSTACK_MOMO_BANK_CODE_MAP = {
    # MTN
    'mtn': 'mtn',
    'mtnmomo': 'mtn',
    'mtnmobilemoney': 'mtn',

    # ATMoney & Airtel Money
    'atl': 'atl',
    'atmoney': 'atl',
    'airtelmoney': 'atl',
    'airteltigo': 'atl',
    'tigo': 'atl',
    'tigocash': 'atl',

    # Vodafone
    'vod': 'vod',
    'vodafone': 'vod',
    'vodafonemoney': 'vod',
}


# email settings
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_MAIL')

# SMS SETTINGS
SENDER_ID = os.getenv('SMS_SENDER_ID') # 11 characters max
ARKESEL_API_KEY = os.getenv('ARKESEL_SMS_API_KEY')

# DRF Spectacular settings
SPECTACULAR_SETTINGS = {
    'TITLE': 'Oysloe Core API',
    'DESCRIPTION': 'Oysloe marketplace API',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}