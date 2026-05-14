# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

"""
Module : equipements.admin
--------------------------
Ce module configure l’interface d’administration Django pour l’application
`equipements`. Il définit comment les modèles `Equipement`, `Creneau`,
`PlageLimite` et `Tarif` apparaissent dans le site d’administration.

Principaux points :
- Déclare des inlines pour gérer directement les créneaux, plages limites
  et tarifs depuis la fiche d’un équipement.
- Personnalise la liste des équipements avec filtres et recherche.
"""

from django.contrib import admin
from usager.models import Affiliation
from .models import Equipement, Creneau, PlageLimite, Tarif, TarifFormation  



class UsagerAdmin(admin.ModelAdmin):
    """
    (Actuellement non utilisé ici.)
    Classe prévue pour personnaliser l’affichage des usagers dans l’admin.
    """
    pass


class CreneauInline(admin.TabularInline):
    """
    Inline admin pour gérer les créneaux horaires d’un équipement
    directement depuis la page de l’équipement.
    - `extra = 0` : aucun formulaire vide affiché par défaut.
    """
    model = Creneau
    extra = 1


class PlageLimiteInline(admin.TabularInline):
    """
    Inline admin pour gérer les plages limites d’un équipement
    (restrictions horaires, durées max).
    - `extra = 0` : aucun formulaire vide affiché par défaut.
    """
    model = PlageLimite
    extra = 1


class TarifInline(admin.TabularInline):
    """
    Inline admin pour gérer les tarifs associés à un équipement.
    - `extra = 1` : affiche une ligne vide par défaut pour saisir un nouveau tarif.
    - Peut être transformé en `StackedInline` si on veut plus d’espace
      (utile si beaucoup de champs dans Tarif).
    """
    model = Tarif
    extra = 1

# Inline admin pour les tarifs de formation
class TarifFormationInline(admin.TabularInline):
    """
    Inline admin pour gérer les tarifs FIXES de formation d’un équipement.
    """
    model = TarifFormation
    extra = 1
    
@admin.register(Equipement)
class EquipementAdmin(admin.ModelAdmin):
    """
    Configuration de l’affichage des équipements dans l’admin Django.
    - `list_display` : colonnes affichées dans la liste des équipements.
    - `list_filter`  : filtres disponibles sur le côté.
    - `search_fields`: champs sur lesquels la recherche admin est possible.
    - `inlines`      : permet de gérer directement créneaux, plages limites
                       et tarifs depuis la fiche d’un équipement.
    """
    list_display = ('nom', 'type', 'localisation', 'actif')
    list_filter = ('type', 'actif')
    search_fields = ('nom', 'localisation')
    inlines = [CreneauInline, PlageLimiteInline, TarifInline, TarifFormationInline]

