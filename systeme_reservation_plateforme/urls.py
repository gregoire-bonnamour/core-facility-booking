# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

"""
Fichier : systeme_reservation_plateforme/urls.py
------------------------------------------------
Définit toutes les routes principales du projet.

Chaque app déclare ses propres `urls.py` (reserv, user_profile, facturation).
Elles sont incluses ici pour centraliser la configuration.
"""

from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.views import LoginView
from accounts.forms import EmailLoginForm
from systeme_reservation_plateforme import views as core_views
from accounts import views as usager_views
from django.contrib.auth import views as auth_views
from django.conf.urls.i18n import i18n_patterns

urlpatterns = [

    # Page de connexion personnalisée
    # - Utilise le template registration/login.html
    # - Remplace le formulaire par EmailLoginForm (auth par email)
    path(
        'accounts/login/',
        LoginView.as_view(
            template_name='registration/login.html',
            authentication_form=EmailLoginForm
        ),
        name='login'
    ),
    # Autres routes d’auth Django (logout, reset password, etc.)
    path('accounts/', include('django.contrib.auth.urls')),

    # App "réservation"
    path('reserv/', include('booking.urls')),

    # Page d’accueil du projet (vue core)
    path('', core_views.accueil, name='accueil'),

    # App "accounts" (gestion inscriptions, profils, invitations…)
    path('user_profile/', include('accounts.urls')),

    # App "billing" (interface génération factures)
    path('facturation/', include('billing.urls')),
        
    path("admin/", admin.site.urls),
    
    path("mot-de-passe/oubli/",
         auth_views.PasswordResetView.as_view(
             template_name="registration/password_reset_form.html",
             email_template_name="registration/password_reset_email.txt",
             subject_template_name="registration/password_reset_subject.txt",
         ),
         name="password_reset"),

    path("mot-de-passe/oubli/ok/",
         auth_views.PasswordResetDoneView.as_view(
             template_name="registration/password_reset_done.html"
         ),
         name="password_reset_done"),

    path("mot-de-passe/reinitialiser/<uidb64>/<token>/",
         auth_views.PasswordResetConfirmView.as_view(
             template_name="registration/password_reset_confirm.html"
         ),
         name="password_reset_confirm"),

    path("mot-de-passe/reinitialiser/termine/",
         auth_views.PasswordResetCompleteView.as_view(
             template_name="registration/password_reset_complete.html"
         ),
         name="password_reset_complete"),
         
    path("", include("ops.urls")), 
    
]

