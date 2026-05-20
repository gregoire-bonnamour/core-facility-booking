# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

"""
Module : facturation.apps
-------------------------
Définit la configuration de l’application Django `facturation`.

Cette classe est utilisée par Django pour enregistrer l’app au démarrage
du projet. C’est également l’endroit où l’on peut ajouter des signaux ou
toute logique d’initialisation propre à l’application.
"""

from django.apps import AppConfig


class BillingConfig(AppConfig):
    """
    Configuration de l’application `facturation`.

    Attributs :
        default_auto_field (str) : type de clé primaire par défaut pour
            les modèles (ici `BigAutoField` → entier 64 bits auto-incrémenté).
        name (str) : chemin Python de l’app (`facturation`).
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'billing'
