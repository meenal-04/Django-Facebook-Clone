"""
Django settings for Connectly.

Local development: SQLite + local media files.
Production: Supabase PostgreSQL + Supabase Storage (S3-compatible).
"""

from pathlib import Path
import os

import dj_database_url
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Security ─────────────────────────────────────────
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "django-insecure-dev-key-change-me")
DEBUG = os.getenv("DEBUG", "True") == "True"

ALLOWED_HOSTS = [
    ".vercel.app",
    "localhost",
    "127.0.0.1",
]
if os.getenv("ALLOWED_HOSTS"):
    ALLOWED_HOSTS += [h.strip() for h in os.getenv("ALLOWED_HOSTS").split(",") if h.strip()]

# ── Apps ─────────────────────────────────────────────
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "core",
]

# ── Middleware ───────────────────────────────────────
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

# ── Templates ────────────────────────────────────────
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.sidebar_data",
            ],
        },
    },
]

# ── Database ─────────────────────────────────────────
# Local: SQLite (safe, fast, zero-config for dev).
# Production: Supabase PostgreSQL via DATABASE_URL env var.
if DEBUG:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": dj_database_url.config(
            default=os.getenv("DATABASE_URL"),
            conn_max_age=600,
            ssl_require=True,
        )
    }

# ── Passwords ────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ── i18n ─────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ── Static files ─────────────────────────────────────
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"] # This tells Django where to find your images
STATIC_ROOT = BASE_DIR / "staticfiles_build"

_static_dir = BASE_DIR / "static"
# STATICFILES_DIRS = [_static_dir] if _static_dir.exists() else []

# ── Media files ──────────────────────────────────────
# Local dev: saved to MEDIA_ROOT on disk.
# Production: uploaded to Supabase Storage (Phase 9).
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

if not DEBUG and os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_KEY"):
    # Production-only Supabase Storage via S3-compatible endpoint.
    AWS_ACCESS_KEY_ID = os.getenv("SUPABASE_S3_ACCESS_KEY")
    AWS_SECRET_ACCESS_KEY = os.getenv("SUPABASE_S3_SECRET_KEY")
    AWS_STORAGE_BUCKET_NAME = os.getenv("SUPABASE_BUCKET", "media")
    AWS_S3_ENDPOINT_URL = f"{os.getenv('SUPABASE_URL')}/storage/v1/s3"
    AWS_S3_REGION_NAME = os.getenv("SUPABASE_REGION", "ap-south-1")
    AWS_S3_ADDRESSING_STYLE = "path"
    AWS_S3_SIGNATURE_VERSION = "s3v4"
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = False

    MEDIA_URL = (
        f"{os.getenv('SUPABASE_URL')}/storage/v1/object/public/"
        f"{AWS_STORAGE_BUCKET_NAME}/"
    )

    STORAGES = {
        "default": {"BACKEND": "storages.backends.s3.S3Storage"},
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
        },
    }
else:
    # Local dev uses simple filesystem storage.
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"
        },
    }

# ── Auth redirects ───────────────────────────────────
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "feed"
LOGOUT_REDIRECT_URL = "login"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Console emails for password reset (dev only)
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# ── Vercel prod extras ───────────────────────────────
CSRF_TRUSTED_ORIGINS = []
if os.getenv("CSRF_TRUSTED_ORIGINS"):
    CSRF_TRUSTED_ORIGINS = [
        o.strip() for o in os.getenv("CSRF_TRUSTED_ORIGINS").split(",") if o.strip()
    ]
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True