"""
Django settings for quote_app project.

Generated by 'django-admin startproject' using Django 5.1.5.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

from pathlib import Path
import os 

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-d#*8x^fu5$!k0=h1roo+b_@050^i(lucf*-^*47@md8t&d718o'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = ["*"]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third party apps
    'crispy_forms',
    'crispy_tailwind',

    # local_apps
    'session',
    'quote',
]

STATIC_URL = 'static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',  # Archivos estáticos globales
]
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Middleware config
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Mover aquí, justo después de SecurityMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'quote_app.middleware.AuthenticationMiddleware',
]

LOGIN_REDIRECT_URL = 'quote/home'

DATA_UPLOAD_MAX_NUMBER_FIELDS = 100000

# URL del login
LOGIN_URL = 'session:login'

ROOT_URLCONF = 'quote_app.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'quote_app.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_USER_MODEL = 'quote.User'

# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Crispy Forms Configuration
CRISPY_ALLOWED_TEMPLATE_PACKS = "tailwind"
CRISPY_TEMPLATE_PACK = "tailwind"

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / ".env"
from pathlib import Path
load_dotenv(dotenv_path=env_path)
import os


PORT: int = int(os.getenv("PORT", 8080))
MAIL_FROM_NAME: str = os.getenv("MAIL_FROM_NAME")
MAIL_FROM_EMAIL: str = os.getenv("MAIL_FROM_EMAIL")
MAIL_SERVER: str = os.getenv("MAIL_SERVER")
MAIL_PORT: int = int(os.getenv("MAIL_PORT", 587))  # Valor predeterminado 587
MAIL_USERNAME: str = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD: str = os.getenv("MAIL_PASSWORD")
MAIL_TLS: bool = os.getenv("MAIL_TLS", "True").lower() in ("true", "1")
BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#INTERNAL_QUOTE_EMAIL: str= os.getenv("INTERNAL_QUOTE_EMAIL")
INTERNAL_QUOTE_EMAIL: str= 'hector_dominguez@grupoarga.com'
QUOTE_REPLY_EMAIL: str = os.getenv("QUOTE_REPLY_EMAIL")

ENABLE_PDF_CONVERSION = True

