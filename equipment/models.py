# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NoCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

"""
Module: equipment_set.models
---------------------------
Ce module définit les modèles de base liés à la gestion des équipements :
- Equipment : objet principal (microscope, cytomètre, etc.)
- TimeSlot    : créneaux horaires autorisés pour réserver l’équipement
- UsageQuota: plages horaires où la durée d’utilisation est plafonnée
- Rate      : grille tarifaire selon l’affiliation de l’user_profile
"""

from django.db import models

class Equipment(models.Model):
    """
    Represents un équipement qui peut être réservé.
    
    Attributs :
        name (str)                : name unique de l’équipement
        description (str)        : description libre de l’équipement
        type (str)               : catégorie (microscope, cytomètre, etc.)
        location (str)       : salle ou lieu de l’équipement
        is_active (bool)             : permet de désactiver l’équipement (masqué des user_profiles)
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    max_duration_hours = models.PositiveIntegerField(
        default=72,  # valeur by default
        help_text="Durée max d'une réservation en heures (sauf demande exceptionnelle)."
    )
    
    TYPE_CHOICES = [
        ('microscope', 'Microscope'),
        ('cytomètre', 'Cytomètre'),
        ('analyse', 'Poste d’analyse'),
        ('autre', 'Autre'),
    ]
    type = models.CharField(max_length=50, choices=TYPE_CHOICES, default='autre')

    location = models.CharField(
        max_length=100,
        help_text="Lieu ou salle où se trouve l'équipement"
    )

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


# -----------------------
# Constantes communes
# -----------------------
DAYS_OF_WEEK = [
    (0, 'Monday'),
    (1, 'Tuesday'),
    (2, 'Wednesday'),
    (3, 'Thursday'),
    (4, 'Friday'),
    (5, 'Saturday'),
    (6, 'Sunday'),
]


class TimeSlot(models.Model):
    """
    Définit un créneau horaire régulier pour un équipement.
    
    Règle métier :
        Une réservation qui commence ou se termine dans un créneau
        doit obligatoirement être entièrement contenue dans ce créneau.
    
    Attributs :
        equipment (Equipment) : link to l’équipement concerné
        day_of_week (int)              : day_of_week de la semaine (0 = Lundi)
        start_time (time)      : début du créneau
        end_time (time)        : fin du créneau
    """
    equipment = models.ForeignKey(
        'Equipment',
        on_delete=models.CASCADE,
        related_name='time_slots',
        help_text="Equipment this time slot belongs to."
    )
    day_of_week = models.IntegerField(
        choices=DAYS_OF_WEEK,
        help_text="Day of the week (0 = Monday, 6 = Sunday)."
    )
    start_time = models.TimeField(help_text="Slot start time (e.g. 08:00).")
    end_time = models.TimeField(help_text="Slot end time (e.g. 12:00).")

    def __str__(self):
        return f"{self.get_day_of_week_display()} {self.start_time.strftime('%H:%M')}–{self.end_time.strftime('%H:%M')} ({self.equipment.name})"

    class Meta:
        verbose_name = "Time Slot"
        verbose_name_plural = "Time Slots"
        ordering = ['equipment', 'day_of_week', 'start_time']


class UsageQuota(models.Model):
    """
    Définit une plage horaire hebdomadaire où la durée totale de réservation
    est limitée pour chaque user_profile.
    
    Example:
        - Microscope, lundi 8h–12h
        - Limite à 120 minutes → un user_profile ne peut pas réserver plus de 2h au total dans cette plage
    
    Attributs :
        equipment (Equipment) : link to l’équipement
        day_of_week (int)              : day_of_week de la semaine (0 = Lundi)
        start_time (time)      : début de la plage
        end_time (time)        : fin de la plage
        max_duration_minutes (int) : durée max cumulée autorisée par user_profile
    """
    equipment = models.ForeignKey(
        'Equipment',
        on_delete=models.CASCADE,
        related_name='usage_quotas',
        help_text="Equipment this usage quota applies to."
    )
    day_of_week = models.IntegerField(choices=DAYS_OF_WEEK, help_text="Day of the week (0 = Monday, etc.).")
    start_time = models.TimeField(help_text="Start of the controlled time window.")
    end_time = models.TimeField(help_text="End of the controlled time window.")
    max_duration_minutes = models.PositiveIntegerField(
        help_text="Maximum cumulative duration allowed per user within this window (in minutes)."
    )

    def __str__(self):
        return f"{self.get_day_of_week_display()} {self.start_time.strftime('%H:%M')}–{self.end_time.strftime('%H:%M')} ({self.max_duration_minutes} min)"

    class Meta:
        verbose_name = "Usage Quota"
        verbose_name_plural = "Usage Quotas"
        ordering = ['equipment', 'day_of_week', 'start_time']

class Rate(models.Model):

    """
    Définit le tarif horaire associés à un équipement pour une affiliation donnée.

    hourly_rate    : coût horaire standard pour l’utilisation de l’équipement

    Attributs :
        equipment (Equipment)   : équipement concerné
        affiliation (Affiliation) : affiliation de l’user_profile (YourUniversity, McGill, UdeM…)
        hourly_rate (Decimal)   : tarif standard en CAD/h

    Constraints:
        - UniqueConstraint : prevents de définir deux rates différents
          pour le même couple (équipement, affiliation).
    """

    equipment = models.ForeignKey("Equipment", on_delete=models.CASCADE, related_name="rates")
    affiliation = models.ForeignKey("accounts.Affiliation", on_delete=models.CASCADE)
    hourly_rate = models.DecimalField(max_digits=6, decimal_places=2)

    class Meta:
        constraints = [
                models.UniqueConstraint(fields=['equipment', 'affiliation'], name='unique_tarif')
            ]
        verbose_name = "Rate"
        verbose_name_plural = "Rates"

    def __str__(self):
        return f"{self.equipment.name} - {self.affiliation.name}: {self.hourly_rate} CAD/h"

class TrainingRate(models.Model):
    """
    Définit le tarif FIXE de formation pour un couple (équipement, affiliation).

    Attributs :
        equipment (Equipment)   : équipement concerné
        affiliation (Affiliation) : affiliation de l’user_profile (YourUniversity, McGill, etc.)
        training_fee (Decimal) : prix fixe (CAD) facturé pour la formation

    Constraints:
        - UniqueConstraint : un (équipement, affiliation) ne peut avoir qu’un seul tarif de formation.
    """
    equipment = models.ForeignKey("Equipment", on_delete=models.CASCADE, related_name="training_rates")
    affiliation = models.ForeignKey("accounts.Affiliation", on_delete=models.CASCADE)
    training_fee = models.DecimalField(max_digits=8, decimal_places=2, help_text="Prix fixe (CAD) pour la formation")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['equipment', 'affiliation'], name='unique_training_fee')
        ]
        verbose_name = "Rate formation"
        verbose_name_plural = "Rates formation"

    def __str__(self):
        return f"{self.equipment.name} - {self.affiliation.name}: {self.training_fee} CAD (formation)"