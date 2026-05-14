from .base import *
from .base import _env_bool

DEBUG = True

# Sécurité dev locale
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]
CSRF_TRUSTED_ORIGINS = ["http://127.0.0.1", "http://localhost"]

# Emails 
EMAIL_BACKEND = "django.core.mail.backends.filebased.EmailBackend"
EMAIL_FILE_PATH = BASE_DIR / "sent_emails"   # -> C:\...\src\sent_emails
DEFAULT_FROM_EMAIL = "Plateforme Réservation <no-reply@example.com>"
EMAIL_SUBJECT_PREFIX = "[Django] "

# Confort dev
INSTALLED_APPS = [a for a in INSTALLED_APPS if a != "django_extensions"]
INSTALLED_APPS += ["django_extensions"]

# Pas de forçage HTTPS en dev
FORCE_SSL = _env_bool("FORCE_SSL", False)
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "templates",  # <-- ton C:\...\src\templates
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
    }
]