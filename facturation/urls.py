# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

"""
Module : facturation.urls
-------------------------
Définit les routes (URLs) de l’application `facturation`.

Actuellement :
- Vue principale : génération des factures (PDF + option CSV).
- Préfixées avec `app_name` pour un usage clair de `reverse('facturation:nom')`.

Futures évolutions possibles :
- Export direct CSV
- Détail d’une facture
"""

# facturation/urls.py
from django.urls import path
from . import views

app_name = 'facturation'

urlpatterns = [
    path('', views.generer_factures, name='page_facturation'),
]


