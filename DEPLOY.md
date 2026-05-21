# Copyright (c) 2025 Grégoire Bonnamour
# Licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License (CC BY-NC-SA 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode for details.

# 🚀 Deployment Guide

This document explains how to deploy, configure, and maintain the Django booking platform in production.

---

## 1. Requirements

### Recommended versions
- Python 3.12+
- Django 4.2.x
- PostgreSQL 15+ (or SQLite for testing)
- WeasyPrint ≥ 61
- Ubuntu 22.04 LTS (or equivalent)

### System packages (required by WeasyPrint)
```bash
sudo apt install libpango-1.0-0 libpangoft2-1.0-0 libcairo2 libffi-dev libgdk-pixbuf2.0-0 python3-dev
```

---

## 2. Installation

### Clone the repository
```bash
git clone https://github.com/gregoire-bonnamour/core-facility-booking.git
cd core-facility-booking
```

### Virtual environment
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 3. Environment variables

Create a `.env` file at the project root (copy from the template):

```bash
cp .env.example .env
nano .env
```

Minimal example:

```env
DEBUG=False
SECRET_KEY=change-me
ALLOWED_HOSTS=booking.youruniversity.ca,localhost,127.0.0.1
TIME_ZONE=America/Toronto

# --- Database ---
DATABASE_URL=postgres://user:password@localhost:5432/booking

# --- Email ---
DEFAULT_FROM_EMAIL=noreply@youruniversity.ca
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.youruniversity.ca
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False

# --- Static files ---
STATIC_ROOT=/srv/booking/static
```

---

## 4. Django initialisation

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

---

## 5. Automatic update of past reservations

The `maj_reservations_passees` command marks expired reservations as `status='past'`.

### Run manually
```bash
python manage.py maj_reservations_passees
```

### Shell script (provided)

`scripts/maj_reservations_passees.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

python manage.py maj_reservations_passees
```

---

## 6. Scheduling (choose one)

### Cron (classic)
```cron
10 0,12 * * * /srv/booking/scripts/maj_reservations_passees.sh >> /var/log/booking_cron.log 2>&1
```

### Systemd timer

`/etc/systemd/system/update-reservations.service`
```ini
[Unit]
Description=Update past reservations

[Service]
Type=oneshot
WorkingDirectory=/srv/booking
ExecStart=/srv/booking/scripts/maj_reservations_passees.sh
```

`/etc/systemd/system/update-reservations.timer`
```ini
[Timer]
OnCalendar=*-*-* 00:10,12:10
Persistent=true

[Install]
WantedBy=timers.target
```

### Docker Compose (if used)
```yaml
services:
  update-reservations:
    image: core-facility-booking:latest
    command: ["bash", "-lc", "./scripts/maj_reservations_passees.sh"]
    env_file: [.env]
```

---

## 7. Starting the application

### Development
```bash
python manage.py runserver 0.0.0.0:8000
```

### Production (Gunicorn + Nginx)
```bash
gunicorn systeme_reservation_plateforme.wsgi:application --bind 127.0.0.1:8000 --workers 3
```

Example systemd service:

```ini
[Unit]
Description=Core Facility Booking — Django
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/srv/booking
ExecStart=/srv/booking/.venv/bin/gunicorn systeme_reservation_plateforme.wsgi:application --bind 127.0.0.1:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## 8. Static files & media

### Static files (JS/CSS/images)

In `.env`:
```env
STATIC_ROOT=/srv/booking/static
```

Then:
```bash
python manage.py collectstatic --noinput
```

Configure Nginx to serve this directory:
```nginx
location /static/ {
    alias /srv/booking/static/;
}
```

### Media files (if uploaded files are used)

Create `/srv/booking/media/` and add to `settings.py`:
```python
MEDIA_ROOT = "/srv/booking/media"
MEDIA_URL = "/media/"
```

---

## 9. Email testing

Before going fully live:

```python
python - <<'PY'
from django.core.mail import send_mail
from django.conf import settings
print("Sending test from:", settings.DEFAULT_FROM_EMAIL)
send_mail("SMTP Test", "OK - configuration valid.", settings.DEFAULT_FROM_EMAIL, ["your.email@youruniversity.ca"], fail_silently=False)
print("✅ Email sent successfully.")
PY
```

---

## 10. Logging

Add this block to `settings.py` to centralise production logs:

```python
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{levelname}] {asctime} {name}: {message}",
            "style": "{",
        },
        "simple": {"format": "[{levelname}] {message}", "style": "{"},
    },
    "handlers": {
        "file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": os.path.join(BASE_DIR, "logs", "django.log"),
            "formatter": "verbose",
        },
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "root": {"handlers": ["file", "console"], "level": "INFO"},
    "loggers": {
        "django": {"handlers": ["file", "console"], "level": "INFO", "propagate": False},
        "booking": {"handlers": ["file", "console"], "level": "DEBUG", "propagate": False},
    },
}
```

Create the log directory:
```bash
mkdir -p logs
chmod 755 logs
```

Logs will be written to `logs/django.log`.

---

## 11. Maintenance & updates

```bash
git pull
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart gunicorn
```

---

## 12. Monitoring

| Type | Location | Format |
|---|---|---|
| Django logs | `logs/django.log` | text |
| Email errors | `logs/email_errors.log` | text |
| Cron batch | `/var/log/booking_cron.log` | text |

Watch for:
- HTTP 500 errors in `logs/django.log`
- Email sending failures (if SMTP is unavailable)
- Reservation batch job (via cron or timer)

---

## 13. Contacts

- **Technical contact:** tech@youruniversity.ca
- **Facility manager:** admin@youruniversity.ca
