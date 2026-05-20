# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NoCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

"""
Module: accounts.backends
------------------------
Backend d'authentification personnalise pour Django.

Objectif :
    Permettre l'authentification via l'adresse email
    plutot que par le `username` par defaut de Django.

A activer dans `settings.py` :
    AUTHENTICATION_BACKENDS = [
        'accounts.backends.EmailAuthBackend',
        'django.contrib.auth.backends.ModelBackend',  # fallback
    ]
"""

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from django.core.cache import cache

RATE_LIMIT_ATTEMPTS = 5    # tentatives max avant blocage
RATE_LIMIT_LOCKOUT  = 300  # secondes de blocage (5 minutes)


class EmailAuthBackend(ModelBackend):
    """
    Authentification par adresse email.
    N'autorise PAS les utilisateurs inactifs (is_active=False).
    Bloque une IP apres 5 tentatives echouees pendant 5 minutes.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()

        # Rate limiting par IP
        ip = (request.META.get('REMOTE_ADDR', 'unknown')
              if request else 'unknown')
        cache_key = f'login_attempts_{ip}'
        attempts = cache.get(cache_key, 0)
        if attempts >= RATE_LIMIT_ATTEMPTS:
            return None

        # On accepte soit username, soit email explicite
        email = username or kwargs.get('email')
        if email is None or password is None:
            return None

        try:
            user = UserModel.objects.get(email__iexact=email)
        except UserModel.DoesNotExist:
            cache.set(cache_key, attempts + 1, RATE_LIMIT_LOCKOUT)
            return None

        # Verifie mot de passe ET is_active via user_can_authenticate
        if user.check_password(password) and self.user_can_authenticate(user):
            cache.delete(cache_key)  # reinitialise le compteur apres succes
            return user

        cache.set(cache_key, attempts + 1, RATE_LIMIT_LOCKOUT)
        return None
