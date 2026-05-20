# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

"""
Module : equipment_set.models
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
    Représente un équipement qui peut être réservé.
    
    Attributs :
        name (str)                : name unique de l’équipement
        description (str)        : description libre de l’équipement
        type (str)               : catégorie (microscope, cytomètre, etc.)
        location (str)       : salle ou lieu de l’équipement
        is_active (bool)             : permet de désactiver l’équipement (masqué des usagers)
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    max_duration_hours = models.PositiveIntegerField(
        default=72,  # valeur par défaut
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
JOURS_SEMAINE = [
    (0, 'Lundi'),
    (1, 'Mardi'),
    (2, 'Mercredi'),
    (3, 'Jeudi'),
    (4, 'Vendredi'),
    (5, 'Samedi'),
    (6, 'Dimanche'),
]


class TimeSlot(models.Model):
    """
    Définit un créneau horaire régulier pour un équipement.
    
    Règle métier :
        Une réservation qui commence ou se termine dans un créneau
        doit obligatoirement être entièrement contenue dans ce créneau.
    
    Attributs :
        equipment (Equipment) : lien vers l’équipement concerné
        day_of_week (int)              : day_of_week de la semaine (0 = Lundi)
        start_time (time)      : début du créneau
        end_time (time)        : fin du créneau
    """
    equipment = models.ForeignKey(
        'Equipment',
        on_delete=models.CASCADE,
        related_name='creneaux',
        help_text="Équipement concerné par ce créneau."
    )
    day_of_week = models.IntegerField(
        choices=JOURS_SEMAINE,
        help_text="Jour de la semaine concerné (0 = Lundi, 6 = Dimanche)."
    )
    start_time = models.TimeField(help_text="Heure de début du créneau (ex: 08:00).")
    end_time = models.TimeField(help_text="Heure de fin du créneau (ex: 12:00).")

    def __str__(self):
        return f"{self.get_jour_display()} {self.start_time.strftime('%H:%M')}–{self.end_time.strftime('%H:%M')} ({self.equipment.name})"

    class Meta:
        verbose_name = "Créneau horaire"
        verbose_name_plural = "Créneaux horaires"
        ordering = ['equipment', 'day_of_week', 'start_time']


class UsageQuota(models.Model):
    """
    Définit une plage horaire hebdomadaire où la durée totale de réservation
    est limitée pour chaque user_profile.
    
    Exemple :
        - Microscope, lundi 8h–12h
        - Limite à 120 minutes → un user_profile ne peut pas réserver plus de 2h au total dans cette plage
    
    Attributs :
        equipment (Equipment) : lien vers l’équipement
        day_of_week (int)              : day_of_week de la semaine (0 = Lundi)
        start_time (time)      : début de la plage
        end_time (time)        : fin de la plage
        max_duration_minutes (int) : durée max cumulée autorisée par user_profile
    """
    equipment = models.ForeignKey(
        'Equipment',
        on_delete=models.CASCADE,
        related_name='plages_limite',
        help_text="Équipement concerné par cette plage de limitation."
    )
    day_of_week = models.IntegerField(choices=JOURS_SEMAINE, help_text="Jour de la semaine (0 = Lundi, etc.).")
    start_time = models.TimeField(help_text="Début de la plage horaire contrôlée.")
    end_time = models.TimeField(help_text="Fin de la plage horaire contrôlée.")
    max_duration_minutes = models.PositiveIntegerField(
        help_text="Durée maximale cumulée autorisée par user_profile dans cette plage (en minutes)."
    )

    def __str__(self):
        return f"{self.get_jour_display()} {self.start_time.strftime('%H:%M')}–{self.end_time.strftime('%H:%M')} ({self.max_duration_minutes} min)"

    class Meta:
        verbose_name = "Plage limitée"
        verbose_name_plural = "Plages limitées"
        ordering = ['equipment', 'day_of_week', 'start_time']

class Rate(models.Model):

    """
    Définit le tarif horaire associés à un équipement pour une affiliation donnée.

    hourly_rate    : coût horaire standard pour l’utilisation de l’équipement

    Attributs :
        equipment (Equipment)   : équipement concerné
        affiliation (Affiliation) : affiliation de l’user_profile (YourUniversity, McGill, UdeM…)
        hourly_rate (Decimal)   : tarif standard en CAD/h

    Contraintes :
        - UniqueConstraint : empêche de définir deux rates différents
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

    Contraintes :
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