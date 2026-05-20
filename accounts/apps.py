# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

"""
Module : usager.apps
--------------------
Configuration de l’application `usager` pour Django.

La classe `UsagerConfig` est utilisée par Django pour
initialiser l’app lors du démarrage du projet.
"""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """
    Configuration principale de l’app `usager`.

    Attributs :
        default_auto_field (str) : Définit le type de clé primaire par défaut
                                   (ici, `BigAutoField`).
        name (str)               : Nom interne de l’application.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        """
        Méthode appelée automatiquement au démarrage de Django.

        ➡ Ici, on importe `usager.signals` afin d’enregistrer
        les signaux (ex. : création automatique de profil usager
        lors de la création d’un compte utilisateur).
        """
        import accounts.signals

