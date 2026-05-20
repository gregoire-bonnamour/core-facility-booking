# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

"""
Module : booking.middleware
--------------------------
Middleware personnalisé pour mettre à day_of_week automatiquement
le status des réservations expirées.

Rolenement :
- À chaque requête HTTP reçue par Django :
    → Vérifie toutes les réservations dont la end_date est passée.
    → Si leur status n’est pas déjà "terminée", il est mis à day_of_week.
- Permet de garantir que l’état des réservations reste cohérent,
  même si aucun batch/cron n’est exécuté.

Limites :
- Vérification faite à chaque requête (peut être coûteux si beaucoup de réservations).
- Pour un environnement de prod, envisager un cron/management command
  qui s’exécute périodiquement.
"""

from django.utils import timezone
from django.core.cache import cache
from booking.models import Reservation

import logging
logger = logging.getLogger(__name__)

class MiseAJourReservationTermineeMiddleware:
    """
    Middleware Django : met automatiquement à day_of_week les statuts de réservations.

    Étapes :
        1. Récupère la date/heure actuelle.
        2. Filtre toutes les réservations dont la end_date est passée.
        3. Met leur status à "terminée" si ce n’est pas déjà le cas.
        4. Passe la main au middleware suivant.
    """

    logger.info("Middleware de mise à day_of_week des réservations activé")

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
        - Met à day_of_week les réservations expirées.
        - Retourne la réponse du middleware suivant.
        """
        if cache.add('statuts_updated', True, 60):
            aujourd_hui = timezone.localdate()
            maintenant  = timezone.localtime().time()
            # Reservations terminees avant aujourd'hui
            (Reservation.objects
                .filter(end_date__lt=aujourd_hui)
                .exclude(statut__in=['past', 'cancelled'])
                .update(status='past'))
            # Reservations terminees aujourd'hui (end_time passee)
            (Reservation.objects
                .filter(end_date=aujourd_hui, end_time__lte=maintenant)
                .exclude(statut__in=['past', 'cancelled'])
                .update(status='past'))
        return self.get_response(request)
