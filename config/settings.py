"""
Django settings for Game Night Arranger.

Local development works with no configuration. In production (PythonAnywhere),
set these environment variables in the WSGI file:

    DJANGO_SECRET_KEY      a long random string
    DJANGO_DEBUG           "0"
    DJANGO_ALLOWED_HOSTS   e.g. "yourname.pythonanywhere.com"
    DJANGO_DB_PATH         optional; defaults to db.sqlite3 in the project folder
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if not DEBUG:
        raise RuntimeError("DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is 0")
    SECRET_KEY = "django-insecure-local-development-only"

ALLOWED_HOSTS = [h for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if h]
if DEBUG:
    # Includes Cloudflare quick-tunnel hosts for phone testing.
    ALLOWED_HOSTS += ["localhost", "127.0.0.1", "[::1]", ".trycloudflare.com"]
    CSRF_TRUSTED_ORIGINS = ["https://*.trycloudflare.com"]

# No django.contrib.admin or auth: nothing in the app may show who voted for what.
INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "events",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("DJANGO_DB_PATH", BASE_DIR / "db.sqlite3"),
    }
}

LANGUAGE_CODE = "en-gb"
TIME_ZONE = "Europe/London"
USE_I18N = False
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    CSRF_COOKIE_SECURE = True

# Player cookies last a year so people can come back on the same device.
PLAYER_COOKIE_MAX_AGE = 60 * 60 * 24 * 365
