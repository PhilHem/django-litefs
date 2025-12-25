"""Django settings for LiteFS example project."""

import os
from pathlib import Path

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
# This is an example - DO NOT USE IN PRODUCTION
SECRET_KEY = "django-insecure-example-key-do-not-use-in-production"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")

ALLOWED_HOSTS = ["*"]

# Application definition
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.admin",
    "litefs_django",  # LiteFS Django adapter
    "myapp",  # Our example app
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "litefs_django.middleware.LiteFSMiddleware",  # LiteFS middleware
]

ROOT_URLCONF = "myproject.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "myproject.wsgi.application"

# Database configuration using LiteFS backend
# The database is stored in /litefs/db.sqlite3 (LiteFS mount path)
DATABASES = {
    "default": {
        "ENGINE": "litefs_django.db.backends.litefs",
        "NAME": "db.sqlite3",  # Will be stored in LiteFS mount path
        "OPTIONS": {
            "litefs_mount_path": "/litefs",  # Mount path where LiteFS stores data
            "transaction_mode": "IMMEDIATE",  # Use IMMEDIATE to prevent lock contention
        },
    }
}

# LiteFS configuration for static leader election (V1)
# This demonstrates static leader election - node1 is always primary
LITEFS = {
    "MOUNT_PATH": "/litefs",  # Where LiteFS mounts the replicated database
    "DATA_PATH": "/data",  # Where LiteFS stores its own state
    "DATABASE_NAME": "db.sqlite3",  # Database filename
    "LEADER_ELECTION": "static",  # Use static leader election
    "PRIMARY_HOSTNAME": os.getenv("PRIMARY_HOSTNAME", "node1"),  # Primary node hostname
    "PROXY_ADDR": ":8081",  # LiteFS proxy address
    "ENABLED": True,  # Enable LiteFS
    "RETENTION": "1h",  # Data retention policy
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Logging configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{levelname}] {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "litefs": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "litefs_django": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
