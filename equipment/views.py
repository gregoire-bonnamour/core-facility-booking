# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NoCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

"""
Module: equipment_set.views
--------------------------
Vues (endpoints) liées à l’application `equipment_set`.

À ce stade, noe vue publique n’est exposée : l’administration des
équipements, créneaux, plages limites et rates se fait via le site
d’administration Django.

Bonnes pratiques :
- Centraliser ici les vues de consultation d’équipements (liste/détail),
  ainsi que d’éventuelles APIs REST/JSON si nécessaire.
- Laisser la logique métier dans les modèles ou les services/helpers,
  et garder les vues fines (contrôle des entrées + assemblage du contexte).

Exemples de futures vues possibles (non implémentées) :
- list_equipements(request) : liste des équipements actifs (avec filtres)
- detail_equipement(request, equipement_id) : fiche d’un équipement
- disponibilites(request, equipement_id) : calcul/affichage des créneaux disponibles
"""

from django.shortcuts import render

# None vue n’est définie pour le moment.
# Ajouter ici les roles/CBV (Class-Based Views) au fur et à mesure des besoins.
#
# Exemple de squelette à réutiliser :
#
# from django.contrib.auth.decorators import login_required
# from .models import Equipment
#
# @login_required
# def list_equipements(request):
#     """
#     Affiche la liste des équipements actifs.
#     Filtrage/facettes (type, location) à ajouter si nécessaire.
#     """
#     equipment_set = Equipment.objects.filter(is_active=True).order_by('name')
#     return render(request, 'equipment_set/liste.html', {'equipment': equipment_set})
