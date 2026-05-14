# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

"""
Fichier : systeme_reservation_plateforme/wsgi.py
------------------------------------------------
Point d’entrée WSGI pour déployer l’application Django.

- WSGI (Web Server Gateway Interface) est le standard utilisé par
  la plupart des serveurs web (Gunicorn, uWSGI, mod_wsgi, etc.) 
  pour exécuter une application Python comme Django.
- Ce fichier expose une variable `application` que le serveur WSGI utilisera.
"""

import os
from django.core.wsgi import get_wsgi_application

# Définit le module de configuration Django par défaut
# (ici : settings.py de ton projet)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'systeme_reservation_plateforme.settings')

# Crée l’objet WSGI qui servira de point d’entrée au serveur web
application = get_wsgi_application()
