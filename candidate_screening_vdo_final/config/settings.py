import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
SARVAM_API_KEY = os.environ.get('SARVAM_API_KEY')
SECRET_KEY = 'django-insecure-talentbot-screening-secret-key-change-in-production'
DEBUG = True
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'screening.apps.ScreeningConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [],
    'APP_DIRS': True,
    'OPTIONS': {
        'context_processors': [
            'django.template.context_processors.debug',
            'django.template.context_processors.request',
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages',
        ],
    },
}]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'infoxtec_DBIEEE30ml23062026',
        'USER':'infoxtec_DBIEEE30ml23062026',
        'PASSWORD':'infoxtec_DBIEEE30ml23062026',
        'HOST':'localhost',
        'PORT':'3306'
    }
}

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
WHITENOISE_MANIFEST_STRICT = False
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
INTERVIEW_MEDIA_ROOT = BASE_DIR / 'interview_media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Auth ────────────────────────────────────────────────────────────────
LOGIN_URL = '/hr/login/'
LOGIN_REDIRECT_URL = '/dashboard/'

# ── Session ─────────────────────────────────────────────────────────────
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 86400          # 24 hours
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = False       # Set True when using HTTPS

# ── CSRF ────────────────────────────────────────────────────────────────
CSRF_USE_SESSIONS = False           # Store token in cookie (not session)
CSRF_COOKIE_HTTPONLY = False        # JS must read it — DO NOT set True
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SECURE = False          # Set True when using HTTPS
CSRF_COOKIE_AGE = 31449600          # 1 year — prevents cookie expiry mid-session
CSRF_ROTATE_TOKEN = False           # Don't rotate token on login → prevents back-button 403
CSRF_TRUSTED_ORIGINS = [
    'http://127.0.0.1:8000',
    'http://localhost:8000',
    'http://127.0.0.1',
    'http://localhost',
    'https://website132.altostechnologies.in',
    'http://website132.altostechnologies.in',
]
