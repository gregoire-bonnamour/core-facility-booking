# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NoCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

"""
Module: user_profile.signals
-----------------------
Définit les signaux liés à l’application `user_profile`.

Objectif principal :
- Créer automatiquement un profil `UserProfile` associé lorsqu’un `User`
  (authentification Django) est créé.

⚠️ Ce module est importé au démarrage de l’app dans `apps.py` (méthode ready).
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile


@receiver(post_save, sender=User)
def creer_usager_associe(sender, instance, created, **kwargs):
    """
    Crée automatiquement un profil UserProfile lors de la création d’un User.

    Args:
        sender   : modèle émetteur du signal (ici `User`).
        instance : instance de User sauvegardée.
        created  : bool, True si le User vient d’être créé.
        **kwargs : paramètres additionnels du signal.
    """
    if created:
        # On s’assure de ne pas dupliquer si déjà lié
        if not hasattr(instance, 'user_profile'):
            UserProfile.objects.create(
                user=instance,
                first_name=instance.first_name or "",
                name=instance.last_name or "",
                email=instance.email or ""
            )
