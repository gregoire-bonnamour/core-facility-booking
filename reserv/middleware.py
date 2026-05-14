# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

"""
Module : reserv.middleware
--------------------------
Middleware personnalisé pour mettre à jour automatiquement
le statut des réservations expirées.

Fonctionnement :
- À chaque requête HTTP reçue par Django :
    → Vérifie toutes les réservations dont la date_fin est passée.
    → Si leur statut n’est pas déjà "terminée", il est mis à jour.
- Permet de garantir que l’état des réservations reste cohérent,
  même si aucun batch/cron n’est exécuté.

Limites :
- Vérification faite à chaque requête (peut être coûteux si beaucoup de réservations).
- Pour un environnement de prod, envisager un cron/management command
  qui s’exécute périodiquement.
"""

from django.utils import timezone
from django.core.cache import cache
from reserv.models import Reservation

import logging
logger = logging.getLogger(__name__)

class MiseAJourReservationTermineeMiddleware:
    """
    Middleware Django : met automatiquement à jour les statuts de réservations.

    Étapes :
        1. Récupère la date/heure actuelle.
        2. Filtre toutes les réservations dont la date_fin est passée.
        3. Met leur statut à "terminée" si ce n’est pas déjà le cas.
        4. Passe la main au middleware suivant.
    """

    logger.info("Middleware de mise à jour des réservations activé")

    def __init__(self, get_response):
        """
        Initialisation du middleware.
        Paramètre :
            get_response (callable) : fonction représentant le middleware suivant.
        """
        self.get_response = get_response

    def __call__(self, request):
        """
        Exécuté pour chaque requête :
        - Met à jour les réservations expirées.
        - Retourne la réponse du middleware suivant.
        """
        if cache.add('statuts_updated', True, 60):
            aujourd_hui = timezone.localdate()
            maintenant  = timezone.localtime().time()
            # Reservations terminees avant aujourd'hui
            (Reservation.objects
                .filter(date_fin__lt=aujourd_hui)
                .exclude(statut__in=['passee', 'annulee'])
                .update(statut='passee'))
            # Reservations terminees aujourd'hui (heure_fin passee)
            (Reservation.objects
                .filter(date_fin=aujourd_hui, heure_fin__lte=maintenant)
                .exclude(statut__in=['passee', 'annulee'])
                .update(statut='passee'))
        return self.get_response(request)
