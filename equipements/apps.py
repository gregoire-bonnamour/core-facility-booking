# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

"""
Module : equipements.apps
-------------------------
Ce module définit la configuration de l’application Django `equipements`.

Django utilise cette classe pour enregistrer et initialiser l’app au démarrage
du projet. On peut aussi y ajouter ultérieurement des signaux ou des paramètres
spécifiques à l’application.
"""

from django.apps import AppConfig


class EquipementsConfig(AppConfig):
    """
    Configuration de l’application `equipements`.

    Attributs :
        default_auto_field (str) : définit le type de clé primaire par défaut
            pour les modèles de l’app (ici `BigAutoField`).
        name (str) : chemin Python de l’app (`equipements`).
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'equipements'
