# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

"""
Module : reserv.models
----------------------
Modèles liés aux réservations d'équipements.

Contenu :
- Reservation : représente une réservation d'un équipement par un usager,
  avec informations de période, assistance, formation, statut, etc.

Notes & bonnes pratiques :
- Les règles de validation se trouvent côté formulaires (reserv/forms.py) et/ou vues.
- Le statut évolue selon la vie de la réservation (à venir → passée/annulée…).
- Les champs d'assistance permettent d'ajouter un coût d'assistance séparé
  (voir facturation/utils.py pour l'usage).
"""

from django.db import models
from equipment.models import Equipement
from accounts.models import Usager
from datetime import datetime
from django.utils import timezone
from django.core.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)


class Reservation(models.Model):
    # --- Liens ---
    usager = models.ForeignKey(Usager, on_delete=models.CASCADE)
    equipement = models.ForeignKey(Equipement, on_delete=models.CASCADE)

    # --- Période ---
    date_debut = models.DateField()
    heure_fin = models.TimeField()
    heure_debut = models.TimeField()
    date_fin = models.DateField()

    # --- Assistance & formation ---
    assistance = models.BooleanField(default=False)
    duree_assistance_minutes = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Durée de l'assistance technique en minutes (rempli par un admin)"
    )
    est_formation = models.BooleanField(default=False)
    courriels_formes = models.TextField(
        blank=True,
        help_text="Uniquement pour les réservations de type formation. Séparer les courriels par des virgules."
    )

    # --- Demande exceptionnelle ---
    demande_exception = models.BooleanField(default=False)
    justification = models.TextField(blank=True)

    # --- Maintenance / Hors service ---
    est_maintenance = models.BooleanField(
        default=False,
        help_text="Réservation pour maintenance/hors service (bloque l'équipement)"
    )

    est_enseignement = models.BooleanField(
        default=False,
        help_text="Réservation pour enseignement (cours de labo)"
    )

    # --- Statut ---
    STATUT_CHOIX = [
        ('a_venir', 'À venir'),
        ('passee', 'Passée'),
        ('annulee', 'Annulée'),
        ('en_attente', 'En attente (exception)'),
    ]
    statut = models.CharField(max_length=20, choices=STATUT_CHOIX, default='a_venir')

    date_creation = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_debut', 'heure_debut']
        verbose_name = "Réservation"
        verbose_name_plural = "Réservations"

    def __str__(self):
        return f"{self.equipement.nom} - {self.date_debut} ({self.heure_debut}-{self.heure_fin})"

    # ---------- Validations métier ----------
    def clean(self):
        errors = {}
        try:
            dt_debut = datetime.combine(self.date_debut, self.heure_debut)
            dt_fin = datetime.combine(self.date_fin, self.heure_fin)
        except Exception:
            dt_debut = dt_fin = None

        if dt_debut and dt_fin and dt_fin <= dt_debut:
            errors['date_fin'] = "La fin doit être strictement postérieure au début."

        if dt_debut and dt_fin and self.equipement_id:
            candidats = (
                Reservation.objects
                .filter(equipement_id=self.equipement_id)
                .exclude(pk=self.pk)
                .exclude(statut='annulee')
                .filter(date_debut__lte=self.date_fin, date_fin__gte=self.date_debut)
            )
            for other in candidats:
                o_debut = datetime.combine(other.date_debut, other.heure_debut)
                o_fin = datetime.combine(other.date_fin, other.heure_fin)
                if dt_debut < o_fin and dt_fin > o_debut:
                    errors['date_debut'] = (
                        "Chevauchement détecté avec une autre réservation de cet équipement."
                    )
                    break

        if errors:
            raise ValidationError(errors)

    # ---------- Statut auto ----------
    def save(self, *args, force_statut: bool = False, skip_invitations: bool = False, **kwargs):
        if self.statut == "annulee":
            force_statut = True

        if not force_statut:
            try:
                now_local = timezone.localtime(timezone.now())
                dt_fin = timezone.make_aware(datetime.combine(self.date_fin, self.heure_fin), now_local.tzinfo)
                if now_local >= dt_fin:
                    if self.statut != "passee":
                        self.statut = "passee"
                else:
                    self.statut = "en_attente" if self.demande_exception else "a_venir"
            except Exception:
                logger.exception("Erreur recalcul statut réservation %s", self.pk)

        super().save(*args, **kwargs)

        if not skip_invitations and self.est_formation and self.statut != "annulee":
            try:
                # Empêcher l'envoi d'invitations pour des formations passées (archivage)
                # Si la formation se termine avant aujourd'hui, on ne fait rien.
                now_local = timezone.localtime(timezone.now())
                dt_fin = timezone.make_aware(datetime.combine(self.date_fin, self.heure_fin), now_local.tzinfo)

                if dt_fin >= now_local:
                    from accounts.utils import creer_invitations_pour_formation
                    # Détecter si l'horaire a changé — si oui, renvoyer à tout le monde
                    force_resend = True
                    if self.pk:
                        try:
                            old = Reservation.objects.get(pk=self.pk)
                            force_resend = (
                                old.date_debut != self.date_debut or
                                old.date_fin != self.date_fin or
                                old.heure_debut != self.heure_debut or
                                old.heure_fin != self.heure_fin
                            )
                        except Reservation.DoesNotExist:
                            force_resend = True
                    creer_invitations_pour_formation(self, force_resend=force_resend)
            except Exception:
                logger.exception("Erreur lors de la génération des invitations (formation=%s)", self.pk)

    @property
    def duree_heures(self) -> float:
        dt_debut = datetime.combine(self.date_debut, self.heure_debut)
        dt_fin = datetime.combine(self.date_fin, self.heure_fin)
        return max((dt_fin - dt_debut).total_seconds() / 3600.0, 0.0)
