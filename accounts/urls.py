# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NoCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

"""
Module: user_profile.urls
--------------------
Définit les routes de l’application `user_profile`.

Rolenalités couvertes :
- Inscription et confirmation par email
- Invitation par administrateur
- Gestion du profil
- Validation des formations
- API AJAX (liste des laboratories par affiliation)
"""

from django.urls import path
from django.views.generic import TemplateView
from . import views

app_name = 'accounts'

urlpatterns = [
    # --- Inscription ---
    path('inscription/', views.inscription, name='inscription'),
    path(
        "confirmation-envoyee/",
        TemplateView.as_view(template_name="accounts/inscription_confirmation.html"),
        name="inscription_confirmation"
    ),
    path('confirmation/<uidb64>/<token>/', views.confirmer_inscription, name='confirmation'),

    # --- Invitation (admin) ---
    path('inviter/', views.inviter_usager, name='invite_user'),

    # --- Profil ---
    path('profil/', views.profil, name='profil'),
    path('admin/user_profile/valider-formations/', views.valider_formations, name='valider_formations'),

    # --- AJAX ---
    path('ajax/labos/', views.get_laboratoires_par_affiliation, name='ajax_labs'),
    
    # Re-verification 5 ans
    path('confirmer-activite/<str:token>/', views.confirmer_activite, name='confirm_activity'),

    # Reglement
    path("reglement/", views.reglement, name="reglement"),
    path('reglement/lecture/', views.reglement_lecture, name='reglement_lecture'),

]
