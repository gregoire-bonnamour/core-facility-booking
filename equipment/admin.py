# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

"""
Module : equipment_set.admin
--------------------------
Ce module configure l’interface d’administration Django pour l’application
`equipment_set`. Il définit comment les modèles `Equipment`, `TimeSlot`,
`UsageQuota` et `Rate` apparaissent dans le site d’administration.

Principaux points :
- Déclare des inlines pour gérer directement les créneaux, plages limites
  et rates depuis la fiche d’un équipement.
- Personnalise la liste des équipements avec filtres et recherche.
"""

from django.contrib import admin
from accounts.models import Affiliation
from .models import Equipment, TimeSlot, UsageQuota, Rate, TrainingRate  



class UserProfileAdmin(admin.ModelAdmin):
    """
    (Actuellement non utilisé ici.)
    Classe prévue pour personnaliser l’affichage des usagers dans l’admin.
    """
    pass


class TimeSlotInline(admin.TabularInline):
    """
    Inline admin pour gérer les créneaux horaires d’un équipement
    directement depuis la page de l’équipement.
    - `extra = 0` : aucun formulaire vide affiché par défaut.
    """
    model = TimeSlot
    extra = 1


class UsageQuotaInline(admin.TabularInline):
    """
    Inline admin pour gérer les plages limites d’un équipement
    (restrictions horaires, durées max).
    - `extra = 0` : aucun formulaire vide affiché par défaut.
    """
    model = UsageQuota
    extra = 1


class RateInline(admin.TabularInline):
    """
    Inline admin pour gérer les rates associés à un équipement.
    - `extra = 1` : affiche une ligne vide par défaut pour saisir un nouveau tarif.
    - Peut être transformé en `StackedInline` si on veut plus d’espace
      (utile si beaucoup de champs dans Rate).
    """
    model = Rate
    extra = 1

# Inline admin pour les rates de formation
class TrainingRateInline(admin.TabularInline):
    """
    Inline admin pour gérer les rates FIXES de formation d’un équipement.
    """
    model = TrainingRate
    extra = 1
    
@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    """
    Configuration de l’affichage des équipements dans l’admin Django.
    - `list_display` : colonnes affichées dans la liste des équipements.
    - `list_filter`  : filtres disponibles sur le côté.
    - `search_fields`: champs sur lesquels la recherche admin est possible.
    - `inlines`      : permet de gérer directement créneaux, plages limites
                       et rates depuis la fiche d’un équipement.
    """
    list_display = ('name', 'type', 'location', 'is_active')
    list_filter = ('type', 'is_active')
    search_fields = ('name', 'location')
    inlines = [TimeSlotInline, UsageQuotaInline, RateInline, TrainingRateInline]

