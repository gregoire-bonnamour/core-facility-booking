# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

"""
Module : facturation.admin
--------------------------
Ce module configure l’interface d’administration Django pour l’application
`facturation`.

Objectif :
- Enregistrer ici les modèles de facturation afin de les gérer via le site d’admin.
- Personnaliser l’affichage (listes, filtres, recherche) si nécessaire.

Bonnes pratiques :
- Utiliser `@admin.register(...)` plutôt que `admin.site.register(...)` pour garder
  la déclaration liée à la classe d’admin.
- Limiter la logique à la présentation (colonnes, filtres, actions) : la logique
  métier reste dans les modèles/services.
"""

from django.contrib import admin

# Remarque :
# À ce stade, aucun modèle n’est enregistré.
# Quand les modèles seront prêts (ex. Facture, LigneFacture, Reglement),
# il suffira de les importer et de définir des classes ModelAdmin.

# Exemple (à activer lorsque les modèles existent) :
#
# from .models import Facture, LigneFacture, Reglement
#
# @admin.register(Facture)
# class FactureAdmin(admin.ModelAdmin):
#     """
#     Configuration d’affichage des factures dans l’admin.
#     - list_display : colonnes visibles dans la liste
#     - list_filter  : filtres latéraux
#     - search_fields: champs recherchables
#     """
#     list_display = ('numero', 'client', 'date', 'montant', 'status')
#     list_filter = ('status', 'date')
#     search_fields = ('numero', 'client__nom')
#
# @admin.register(LigneFacture)
# class LigneFactureAdmin(admin.ModelAdmin):
#     """Affichage des lignes de facture (produits/prestations)."""
#     list_display = ('facture', 'designation', 'quantite', 'prix_unitaire', 'total')
#     search_fields = ('facture__numero', 'designation')
#
# @admin.register(Reglement)
# class ReglementAdmin(admin.ModelAdmin):
#     """Affichage des règlements associés aux factures."""
#     list_display = ('facture', 'date', 'montant', 'mode')
#     list_filter = ('mode', 'date')
#     search_fields = ('facture__numero',)
#
# Note : pensez à définir `readonly_fields` si certains champs sont calculés,
# et `inlines` pour éditer des lignes de facture directement depuis la facture.
