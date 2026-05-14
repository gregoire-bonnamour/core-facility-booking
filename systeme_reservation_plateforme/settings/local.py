from .base import *  # noqa
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env.local")   # optionnel pour ton confort
except Exception:
    pass

DEBUG = True

# Clé de dev (OK en local uniquement)
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-secret-change-me")

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# Email -> fichiers (comme aujourd’hui)
EMAIL_BACKEND = "django.core.mail.backends.filebased.EmailBackend"
EMAIL_FILE_PATH = BASE_DIR / "sent_emails"
EMAIL_FILE_PATH.mkdir(parents=True, exist_ok=True)

# Pas de contraintes HTTPS en local
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0
