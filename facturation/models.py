# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

"""
Module : facturation.models
---------------------------
Modèles de données de l'application `facturation`.

À ce stade, aucun modèle n'est défini ici. Les données de facturation
sont probablement calculées à partir d'autres apps (réservations, usagers,
tarifs par affiliation) et exposées via des vues/exports.

Bonnes pratiques pour la suite :
- Créer un modèle `Facture` si l'on souhaite persister les factures
  (numéro, client/affiliation, période couverte, montant, statut, etc.).
- Créer un modèle `LigneFacture` si l'on veut détailler par réservation,
  équipement, ou prestation.
- Prévoir des champs "trace" (date de génération, généré par, version).
- Utiliser des contraintes (UniqueConstraint) pour éviter les doublons
  sur (période, affiliation, laboratoire, etc.).
"""

from django.db import models
# Aucun modèle pour le moment.
# Ajouter ici les classes métier (ex.: Facture, LigneFacture, Règlement)
# lorsque le besoin de persistance sera confirmé.
