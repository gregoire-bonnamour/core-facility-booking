# Copyright (c) 2025 Author Author
# Licensed under the MIT License. See LICENSE file for details.

from pathlib import Path
import os
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parents[2]

# --- Helpers ---
def _env_bool(name, default=False):
    return str(os.getenv(name, str(default))).lower() in ("1", "true", "yes", "on")

SITE_URL = os.getenv("SITE_URL", "http://127.0.0.1:8000")

# --- Core ---
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-key")  # ⚠️ override en prod
DEBUG = _env_bool("DEBUG", True)

ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if h.strip()]
CSRF_TRUSTED_ORIGINS = [u.strip() for u in os.getenv(
    "CSRF_TRUSTED_ORIGINS",
    ",".join(f"http://{h}" for h in ALLOWED_HOSTS)
).split(",") if u.strip()]

# --- Apps ---
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Apps projet
    "equipment",
    "accounts.apps.AccountsConfig",
    "booking",
    "billing",
    'maintenance',
    "ops",
]

# --- Middleware ---
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    # "django.middleware.locale.LocaleMiddleware",  # disabled: force en locale  
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",

    # Middleware applicatifs
    "systeme_reservation_plateforme.middleware.ReglementAcceptanceMiddleware",
    "booking.middleware.MiseAJourReservationTermineeMiddleware",
]

ROOT_URLCONF = "systeme_reservation_plateforme.urls"
WSGI_APPLICATION = "systeme_reservation_plateforme.wsgi.application"

# --- Templates ---
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "templates",  
            BASE_DIR / "systeme_reservation_plateforme" / "templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "systeme_reservation_plateforme.context_processors.support_mailto",
                "systeme_reservation_plateforme.context_processors.news_feed",
            ],
        },
    },
]

# --- DB (by default SQLite, override en prod si besoin) ---
DATABASES = {
    "default": {
        "ENGINE": os.getenv("DB_ENGINE", "django.db.backends.sqlite3"),
        "NAME": os.getenv("DB_NAME", str(BASE_DIR / "db.sqlite3")),
        "USER": os.getenv("DB_USER", ""),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", ""),
        "PORT": os.getenv("DB_PORT", ""),
    }
}

# --- i18n / TZ ---
LANGUAGE_CODE = "en"          # EN for GitHub public repo
TIME_ZONE = "America/Toronto"  # EST/EDT — même fuseau que Montréal
USE_I18N = True
USE_L10N = True
USE_TZ = True

LANGUAGES = (
    ("fr", "Français"),
    ("en", "English"),
)

# --- Static / Media ---
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []
STATIC_ROOT = Path(os.getenv("STATIC_ROOT", BASE_DIR / "static_collected"))

MEDIA_URL = "/media/"
MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", BASE_DIR / "media"))

# --- Auth redirects ---
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

# --- Email (by default sûr: filebased) ---
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.filebased.EmailBackend")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "Booking Platform <no-reply@example.com>")
SERVER_EMAIL = os.getenv("SERVER_EMAIL", "no-reply@example.com")
if EMAIL_BACKEND.endswith("filebased.EmailBackend"):
    EMAIL_FILE_PATH = os.getenv("EMAIL_FILE_PATH", str(BASE_DIR / "sent_emails"))
else:
    EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.office365.com")
    EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
    EMAIL_USE_TLS = _env_bool("EMAIL_USE_TLS", True)
    EMAIL_USE_SSL = _env_bool("EMAIL_USE_SSL", False)
    EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
    EMAIL_TIMEOUT = int(os.getenv("EMAIL_TIMEOUT", "30"))

# --- Sécurité proxy (Nginx/HTTPS en frontal) ---
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# --- Cookies ---
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# --- Password / Admins ---
PASSWORD_RESET_TIMEOUT = int(os.getenv("PASSWORD_RESET_TIMEOUT_SECONDS", str(int(timedelta(hours=48).total_seconds()))))
ADMINS = [("Author", "admin@youruniversity.ca")]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTHENTICATION_BACKENDS = [
    "accounts.backends.EmailAuthBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# --- Logging ---
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
        "mail_admins": {"class": "django.utils.log.AdminEmailHandler", "level": "ERROR"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.request": {"handlers": ["mail_admins", "console"], "level": "ERROR", "propagate": False},
        "booking": {"handlers": ["console"], "level": "INFO"},
        "billing": {"handlers": ["console"], "level": "INFO"},
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOCALE_PATHS = [BASE_DIR / "locale"]