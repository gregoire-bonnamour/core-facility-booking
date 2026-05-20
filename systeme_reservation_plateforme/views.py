# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NoCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

"""
Fichier : systeme_reservation_plateforme/views.py
-------------------------------------------------
Définit les vues "générales" du projet qui ne dépendent pas
d’une application spécifique (ici : la page d’accueil).
"""

from datetime import date, timedelta
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from accounts.models import UserProfile
from booking.models import Reservation


@login_required
def accueil(request):
    """
    Vue principale de la plateforme (page d’accueil).
    
    Affiche un tableau de bord différent selon le rôle :
    - UserProfile : liste de ses équipements autorisés
    - Admin  : accès à l’administration + alertes réservations en attente

    Contexte envoyé au template :
        user : utilisateur Django connecté
        is_admin : booléen → True si staff/admin
        equipment_set : équipements accessibles à l’user_profile
        lundi : date du lundi de la semaine courante
        nb_reservations_en_attente (si admin) : nombre de réservations à valider
    """
    is_platform_admin = request.user.is_staff or (hasattr(request.user, 'accounts') and request.user.user_profile.is_platform_admin)

    equipment_set = []
    try:
        # Récupère le profil étendu lié à l’utilisateur
        user_profile = get_object_or_404(UserProfile, user=request.user)
        equipment_set = user_profile.authorized_equipment.all()
    except UserProfile.DoesNotExist:
        # Si no profil user_profile n’est lié au compte (cas exceptionnel)
        pass  

    # Calcule le lundi de la semaine courante (utile pour affichage du calendrier)
    lundi = date.today() - timedelta(days=date.today().weekday())

    # Construit le contexte pour le template
    context = {
        'user': request.user,
        'is_admin': is_platform_admin,
        'equipment': equipment_set,
        'lundi': lundi,
    }

    # Si l’utilisateur est admin → ajoute les réservations en attente de validation
    if is_platform_admin:
        en_attente = Reservation.objects.filter(status='pending').count()
        context['nb_reservations_en_attente'] = en_attente

    return render(request, 'accueil/accueil.html', context)
