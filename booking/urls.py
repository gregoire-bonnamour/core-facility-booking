# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NoCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

"""
Module: reserv.urls
--------------------
Définit les routes (URLs) pour l'application `reserv`.

Rolenalités couvertes :
- Réservation d'un équipement
- Calendrier par équipement
- Gestion d'une réservation (modifier, supprimer, visualiser, redirection)
- Statistiques (filtres dynamiques AJAX + exports XLSX)
- Accueil des réservations

Bonnes pratiques :
- Utiliser `app_name` pour le namespace → permet d'appeler
  les routes avec `reverse("booking:nom_route")`.
"""

from django.urls import path
from . import views
from booking import views as reserv_views

app_name = 'booking'

urlpatterns = [
    # --- Réservations ---
    path('reserver/<int:equipement_id>/', views.reserver_equipement, name='reserver'),
    path('calendrier/<int:equipement_id>/', views.calendrier_equipement, name='calendar_equipement'),

    # --- Gestion d'une réservation ---
    path('modifier/<int:reservation_id>/', views.modifier_reservation, name='edit_reservation'),
    path('supprimer/<int:reservation_id>/', views.supprimer_reservation, name='delete_reservation'),
    path('visualiser/<int:reservation_id>/', views.visualiser_reservation, name='view_reservation'),
    path('redirection/<int:reservation_id>/', views.rediriger_reservation, name='redirect_reservation'),

    # --- Statistiques ---
    path('stats/', views.stats_admin, name='stats_admin'),
    path('stats/query/', views.stats_query, name='stats_query'),
    path('stats/zone1/', views.stats_zone1, name='stats_zone1'),
    path("admin/reservations/calendrier-global/", views.calendrier_global_admin, name="calendar_global_admin"),
    path("admin/reservations/calendrier-global/data/", views.calendrier_global_admin_data, name="calendar_global_admin_data"),
    path('stats/export/unified/', views.stats_export_unified_xlsx, name='stats_export_unified_xlsx'),
    path('stats/ajax/labos/', views.ajax_labos, name='stats_ajax_labos'),
    path('stats/ajax/user_profiles/', views.ajax_users, name='stats_ajax_users'),
    path('stats/ajax/roles/', views.ajax_fonctions, name='stats_ajax_roles'),
    
    # --- Accueil ---
    path('', views.accueil, name='home'),
]
