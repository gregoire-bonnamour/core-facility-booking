from .base import *  # noqa
from pathlib import Path
import os

# --- Charger .env.prod (au meme niveau que manage.py) ---
try:
    from dotenv import load_dotenv
except ImportError as e:
    raise RuntimeError(
        "python-dotenv n'est pas installe. Fais: pip install python-dotenv"
    ) from e

DOTENV_PATH = BASE_DIR / ".env.prod"
if DOTENV_PATH.exists():
    load_dotenv(DOTENV_PATH)
# sinon: on suppose que les variables sont deja dans l'env (CI/CD, VM)

# --- Helpers ---
def _as_bool(v: str | None, default: bool = False) -> bool:
    if v is None:
        return default
    return str(v).strip().lower() in ("1", "true", "yes", "on")

# --- Parametres essentiels ---
# Exige SECRET_KEY en prod; pour les tests locaux, mets-le dans .env.prod
SECRET_KEY = os.environ["SECRET_KEY"]

DEBUG = _as_bool(os.getenv("DEBUG"), default=False)

# Valeur sure par defaut pour eviter l'exception quand tu testes en local
_default_hosts = "localhost,127.0.0.1"
ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", _default_hosts).split(",") if h.strip()]

# Optionnel: origines CSRF de confiance (laisser vide en local)
CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()
]

# Localisation (herite de base.py si non fourni)
TIME_ZONE = os.getenv("TIME_ZONE", TIME_ZONE)
LANGUAGE_CODE = os.getenv("LANGUAGE_CODE", LANGUAGE_CODE)

# --- Base de donnees (SQLite par defaut) ---
SQLITE_NAME = os.getenv("SQLITE_NAME", "db.sqlite3")
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / SQLITE_NAME,
    }
}

# --- Emails ---
EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    "django.core.mail.backends.filebased.EmailBackend",  # log dans un dossier
)

if EMAIL_BACKEND.endswith("filebased.EmailBackend"):
    EMAIL_FILE_PATH = BASE_DIR / os.getenv("EMAIL_FILE_PATH", "sent_emails")
    try:
        EMAIL_FILE_PATH.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass

DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "webmaster@localhost")

# --- Securite HTTP ---
SECURE_SSL_REDIRECT = _as_bool(os.getenv("FORCE_SSL"), default=True)
SESSION_COOKIE_SECURE = SECURE_SSL_REDIRECT
CSRF_COOKIE_SECURE = SECURE_SSL_REDIRECT

SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = _as_bool(os.getenv("SECURE_HSTS_INCLUDE_SUBDOMAINS"), False)
SECURE_HSTS_PRELOAD = _as_bool(os.getenv("SECURE_HSTS_PRELOAD"), False)

# --- Logging (niveau configurable) ---
DJANGO_LOG_LEVEL = os.getenv("DJANGO_LOG_LEVEL", "INFO").upper()
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "[{levelname}] {asctime} {name}: {message}", "style": "{"},
        "simple": {"format": "[{levelname}] {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "root": {"handlers": ["console"], "level": DJANGO_LOG_LEVEL},
}

# --- override temporaire pour permettre les tests en HTTPS (IP / FQDN interne)
