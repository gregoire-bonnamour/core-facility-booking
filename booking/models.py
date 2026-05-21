# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NoCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

"""
Module: reserv.models
----------------------
Modèles liés aux réservations d'équipements.

Content:
- Reservation : représente une réservation d'un équipement par un user_profile,
  avec informations de période, assistance, formation, status, etc.

Notes & bonnes pratiques :
- Les règles de validation se trouvent côté formulaires (reserv/forms.py) et/ou vues.
- Le status évolue selon la vie de la réservation (à venir → passée/annulée…).
- Les champs d'assistance permettent d'ajouter un coût d'assistance séparé
  (voir facturation/utils.py pour l'usage).
"""

from django.db import models
from equipment.models import Equipment
from accounts.models import UserProfile
from datetime import datetime
from django.utils import timezone
from django.core.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)


class Reservation(models.Model):
    # --- Liens ---
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE)

    # --- Période ---
    start_date = models.DateField()
    end_time = models.TimeField()
    start_time = models.TimeField()
    end_date = models.DateField()

    # --- Assistance & formation ---
    assistance = models.BooleanField(default=False)
    assistance_duration_minutes = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Durée de l'assistance technique en minutes (rempli par un admin)"
    )
    is_training = models.BooleanField(default=False)
    trained_emails = models.TextField(
        blank=True,
        help_text="For training reservations only. Separate emails with commas."
    )

    # --- Demande exceptionnelle ---
    exception_request = models.BooleanField(default=False)
    justification = models.TextField(blank=True)

    # --- Maintenance / Hors service ---
    is_maintenance = models.BooleanField(
        default=False,
        help_text="Maintenance/out-of-service reservation (blocks equipment)"
    )

    is_teaching = models.BooleanField(
        default=False,
        help_text="Teaching reservation (lab course)"
    )

    # --- Statut ---
    STATUT_CHOIX = [
        ('upcoming', 'Upcoming'),
        ('past', 'Past'),
        ('cancelled', 'Cancelled'),
        ('pending', 'Pending (exception request)'),
    ]
    status = models.CharField(max_length=20, choices=STATUT_CHOIX, default='upcoming')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date', 'start_time']
        verbose_name = "Reservation"
        verbose_name_plural = "Reservations"

    def __str__(self):
        return f"{self.equipment.name} - {self.start_date} ({self.start_time}-{self.end_time})"

    # ---------- Validations métier ----------
    def clean(self):
        errors = {}
        try:
            dt_debut = datetime.combine(self.start_date, self.start_time)
            dt_fin = datetime.combine(self.end_date, self.end_time)
        except Exception:
            dt_debut = dt_fin = None

        if dt_debut and dt_fin and dt_fin <= dt_debut:
            errors['end_date'] = "The end time must be strictly after the start time."

        if dt_debut and dt_fin and self.equipment_id:
            candidats = (
                Reservation.objects
                .filter(equipment_id=self.equipment_id)
                .exclude(pk=self.pk)
                .exclude(status='cancelled')
                .filter(start_date__lte=self.end_date, end_date__gte=self.start_date)
            )
            for other in candidats:
                o_debut = datetime.combine(other.start_date, other.start_time)
                o_fin = datetime.combine(other.end_date, other.end_time)
                if dt_debut < o_fin and dt_fin > o_debut:
                    errors['start_date'] = (
                        "Overlap detected with another reservation for this equipment."
                    )
                    break

        if errors:
            raise ValidationError(errors)

    # ---------- Statut auto ----------
    def save(self, *args, force_status: bool = False, skip_invitations: bool = False, **kwargs):
        if self.status == "cancelled":
            force_status = True

        if not force_status:
            try:
                now_local = timezone.localtime(timezone.now())
                dt_fin = timezone.make_aware(datetime.combine(self.end_date, self.end_time), now_local.tzinfo)
                if now_local >= dt_fin:
                    if self.status != "past":
                        self.status = "past"
                else:
                    self.status = "pending" if self.exception_request else "upcoming"
            except Exception:
                logger.exception("Erreur recalcul status réservation %s", self.pk)

        super().save(*args, **kwargs)

        if not skip_invitations and self.is_training and self.status != "cancelled":
            try:
                # Preventsr l'envoi d'invitations pour des formations passées (archivage)
                # Si la formation se termine avant aujourd'hui, on ne fait rien.
                now_local = timezone.localtime(timezone.now())
                dt_fin = timezone.make_aware(datetime.combine(self.end_date, self.end_time), now_local.tzinfo)

                if dt_fin >= now_local:
                    from accounts.utils import creer_invitations_pour_formation
                    # Détecter si l'horaire a changé — si oui, renvoyer à tout le monde
                    force_resend = True
                    if self.pk:
                        try:
                            old = Reservation.objects.get(pk=self.pk)
                            force_resend = (
                                old.start_date != self.start_date or
                                old.end_date != self.end_date or
                                old.start_time != self.start_time or
                                old.end_time != self.end_time
                            )
                        except Reservation.DoesNotExist:
                            force_resend = True
                    creer_invitations_pour_formation(self, force_resend=force_resend)
            except Exception:
                logger.exception("Erreur lors de la génération des invitations (formation=%s)", self.pk)

    @property
    def duree_heures(self) -> float:
        dt_debut = datetime.combine(self.start_date, self.start_time)
        dt_fin = datetime.combine(self.end_date, self.end_time)
        return max((dt_fin - dt_debut).total_seconds() / 3600.0, 0.0)
