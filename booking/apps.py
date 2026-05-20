# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NoCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

"""
Module: reserv.apps
--------------------
Définit la configuration de l’application Django `reserv`.

Cette classe est utilisée par Django pour :
- enregistrer l’application lors du démarrage du projet,
- appliquer des paramètres spécifiques (ex. type de clé primaire by default),
- connecter des signaux si nécessaire (via la méthode ready()).
"""

from django.apps import AppConfig


class BookingConfig(AppConfig):
    """
    Configuration de l’application `reserv`.

    Attributs :
        default_auto_field (str) : définit le type de clé primaire by default
            pour les modèles (ici `BigAutoField`, entier auto-incrémenté 64 bits).
        name (str) : chemin Python de l’application (`reserv`).
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'booking'
