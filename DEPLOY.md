# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

🚀 DEPLOY.md
# 🚀 Déploiement – Système de réservation d’équipements

Ce document explique comment déployer, configurer et maintenir la plateforme Django en production.

---

## 1. Environnement requis

### Versions recommandées
- Python 3.12+
- Django 4.2.x
- PostgreSQL 15+ (ou SQLite pour test)
- WeasyPrint ≥ 61
- Ubuntu 22.04 LTS (ou équivalent)

### Paquets système (pour WeasyPrint)
```bash
sudo apt install libpango-1.0-0 libpangoft2-1.0-0 libcairo2 libffi-dev libgdk-pixbuf2.0-0 python3-dev

2. Installation
Cloner le dépôt
git clone https://github.com/ton-org/systeme-reservation.git
cd systeme-reservation

Environnement virtuel
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

3. Variables d’environnement

Crée un fichier .env à la racine du projet (copie le modèle .env.example) :

cp .env.example .env
nano .env


Exemple minimal :

DEBUG=False
SECRET_KEY=changemoi
ALLOWED_HOSTS=plateforme.univ.ca,localhost,127.0.0.1
TIME_ZONE=America/Toronto

# --- Base de données ---
DATABASE_URL=postgres://user:password@localhost:5432/reservation

# --- Emails ---
DEFAULT_FROM_EMAIL=noreply@univ.ca
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.univ.ca
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False

# --- Fichiers statiques ---
STATIC_ROOT=/srv/plateforme/static

4. Initialisation Django
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser

5. Mise à jour automatique des réservations passées

Le script maj_reservations_passees met à jour les réservations expirées (statut=passee).

Lancer manuellement
python manage.py maj_reservations_passees

Script shell (fourni)

scripts/maj_reservations_passees.sh

#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

python manage.py maj_reservations_passees

6. Planification (au choix)
Cron (classique)
10 0,12 * * * /srv/plateforme/scripts/maj_reservations_passees.sh >> /var/log/resa_cron.log 2>&1

Systemd Timer

/etc/systemd/system/maj-reservations.service

[Unit]
Description=Mise à jour des réservations passées

[Service]
Type=oneshot
WorkingDirectory=/srv/plateforme
ExecStart=/srv/plateforme/scripts/maj_reservations_passees.sh


/etc/systemd/system/maj-reservations.timer

[Timer]
OnCalendar=*-*-* 00:10,12:10
Persistent=true

[Install]
WantedBy=timers.target

Docker Compose (si utilisé)
services:
  maj-reservations:
    image: plateforme-reservation:latest
    command: ["bash", "-lc", "./scripts/maj_reservations_passees.sh"]
    env_file: [.env]

7. Démarrage de l’application
Mode développement
python manage.py runserver 0.0.0.0:8000

Mode production (Gunicorn + Nginx)
gunicorn systeme_reservation_plateforme.wsgi:application --bind 127.0.0.1:8000 --workers 3


Exemple de service systemd :

[Unit]
Description=Plateforme Django de réservation
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/srv/plateforme
ExecStart=/srv/plateforme/.venv/bin/gunicorn systeme_reservation_plateforme.wsgi:application --bind 127.0.0.1:8000
Restart=always

[Install]
WantedBy=multi-user.target

8. Statique & médias
Fichiers statiques (JS/CSS/images)

Dans .env :

STATIC_ROOT=/srv/plateforme/static


Puis :

python manage.py collectstatic --noinput


Configurer Nginx pour servir ce répertoire :

location /static/ {
    alias /srv/plateforme/static/;
}

Médias (si des fichiers uploadés existent)

Prévoir un dossier /srv/plateforme/media et ajouter dans settings.py :

MEDIA_ROOT = "/srv/plateforme/media"
MEDIA_URL = "/media/"

9. Test des emails

Avant la mise en prod complète :

python - <<'PY'
from django.core.mail import send_mail
from django.conf import settings
print("Test envoi depuis:", settings.DEFAULT_FROM_EMAIL)
send_mail("Test SMTP", "OK - configuration valide.", settings.DEFAULT_FROM_EMAIL, ["ton.email@univ.ca"], fail_silently=False)
print("✅ Email envoyé avec succès.")
PY

10. Journalisation (LOGGING)

Ajoute ce bloc dans settings.py pour centraliser les logs en production :

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
        "reserv": {"handlers": ["file", "console"], "level": "DEBUG", "propagate": False},
    },
}


Créer le dossier :

mkdir -p logs
chmod 755 logs


Les logs seront alors enregistrés dans logs/django.log.

11. Maintenance et mises à jour
git pull
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart gunicorn

12. Journalisation et supervision
Type	Emplacement	Format
Django logs	logs/django.log	texte
Emails	logs/email_errors.log	texte
Cron batch	/var/log/resa_cron.log	texte

Surveiller :

Les erreurs HTTP 500 dans logs/django.log

Les envois d’emails (si SMTP indisponible)

Le batch des réservations (via cron ou timer)

13. Contacts

Responsable technique : tech@univ.ca

Responsable fonctionnel : admin-labo@univ.ca


---

### 🧩 Ce que ce `DEPLOY.md` apporte en plus
✅ `.env.example` expliqué et utilisé  
✅ Variables critiques (`STATIC_ROOT`, `ALLOWED_HOSTS`, `TIME_ZONE`)  
✅ Test d’envoi mail rapide  
✅ Bloc LOGGING de production complet et commenté  
✅ Guide clair pour la maintenance et la supervision  
