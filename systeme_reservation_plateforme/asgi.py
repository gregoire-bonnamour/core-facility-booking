# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NoCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

"""
Fichier : systeme_reservation_plateforme/asgi.py
------------------------------------------------
Point d’entrée ASGI pour l’application Django.

- ASGI (Asynchronous Server Gateway Interface) est l’évolution de WSGI,
  conçue pour supporter l’asynchrone (WebSockets, HTTP/2, SSE…).
- Ce fichier expose une variable `application` utilisée par les serveurs ASGI
  (ex : Daphne, Uvicorn, Hypercorn) pour lancer le projet Django.
"""

import os
from django.core.asgi import get_asgi_application

# Définit le module de configuration Django by default
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'systeme_reservation_plateforme.settings')

# Crée l’objet ASGI qui servira de point d’entrée au serveur ASGI
application = get_asgi_application()
