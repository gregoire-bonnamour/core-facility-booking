# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

"""
Module : equipements.models
---------------------------
Ce module définit les modèles de base liés à la gestion des équipements :
- Equipement : objet principal (microscope, cytomètre, etc.)
- Creneau    : créneaux horaires autorisés pour réserver l’équipement
- PlageLimite: plages horaires où la durée d’utilisation est plafonnée
- Tarif      : grille tarifaire selon l’affiliation de l’usager
"""

from django.db import models

class Equipement(models.Model):
    """
    Représente un équipement qui peut être réservé.
    
    Attributs :
        nom (str)                : nom unique de l’équipement
        description (str)        : description libre de l’équipement
        type (str)               : catégorie (microscope, cytomètre, etc.)
        localisation (str)       : salle ou lieu de l’équipement
        actif (bool)             : permet de désactiver l’équipement (masqué des usagers)
    """
    nom = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    duree_max_heures = models.PositiveIntegerField(
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

    localisation = models.CharField(
        max_length=100,
        help_text="Lieu ou salle où se trouve l'équipement"
    )

    actif = models.BooleanField(default=True)

    def __str__(self):
        return self.nom


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


class Creneau(models.Model):
    """
    Définit un créneau horaire régulier pour un équipement.
    
    Règle métier :
        Une réservation qui commence ou se termine dans un créneau
        doit obligatoirement être entièrement contenue dans ce créneau.
    
    Attributs :
        equipement (Equipement) : lien vers l’équipement concerné
        jour (int)              : jour de la semaine (0 = Lundi)
        heure_debut (time)      : début du créneau
        heure_fin (time)        : fin du créneau
    """
    equipement = models.ForeignKey(
        'Equipement',
        on_delete=models.CASCADE,
        related_name='creneaux',
        help_text="Équipement concerné par ce créneau."
    )
    jour = models.IntegerField(
        choices=JOURS_SEMAINE,
        help_text="Jour de la semaine concerné (0 = Lundi, 6 = Dimanche)."
    )
    heure_debut = models.TimeField(help_text="Heure de début du créneau (ex: 08:00).")
    heure_fin = models.TimeField(help_text="Heure de fin du créneau (ex: 12:00).")

    def __str__(self):
        return f"{self.get_jour_display()} {self.heure_debut.strftime('%H:%M')}–{self.heure_fin.strftime('%H:%M')} ({self.equipement.nom})"

    class Meta:
        verbose_name = "Créneau horaire"
        verbose_name_plural = "Créneaux horaires"
        ordering = ['equipement', 'jour', 'heure_debut']


class PlageLimite(models.Model):
    """
    Définit une plage horaire hebdomadaire où la durée totale de réservation
    est limitée pour chaque usager.
    
    Exemple :
        - Microscope, lundi 8h–12h
        - Limite à 120 minutes → un usager ne peut pas réserver plus de 2h au total dans cette plage
    
    Attributs :
        equipement (Equipement) : lien vers l’équipement
        jour (int)              : jour de la semaine (0 = Lundi)
        heure_debut (time)      : début de la plage
        heure_fin (time)        : fin de la plage
        duree_max_minutes (int) : durée max cumulée autorisée par usager
    """
    equipement = models.ForeignKey(
        'Equipement',
        on_delete=models.CASCADE,
        related_name='plages_limite',
        help_text="Équipement concerné par cette plage de limitation."
    )
    jour = models.IntegerField(choices=JOURS_SEMAINE, help_text="Jour de la semaine (0 = Lundi, etc.).")
    heure_debut = models.TimeField(help_text="Début de la plage horaire contrôlée.")
    heure_fin = models.TimeField(help_text="Fin de la plage horaire contrôlée.")
    duree_max_minutes = models.PositiveIntegerField(
        help_text="Durée maximale cumulée autorisée par usager dans cette plage (en minutes)."
    )

    def __str__(self):
        return f"{self.get_jour_display()} {self.heure_debut.strftime('%H:%M')}–{self.heure_fin.strftime('%H:%M')} ({self.duree_max_minutes} min)"

    class Meta:
        verbose_name = "Plage limitée"
        verbose_name_plural = "Plages limitées"
        ordering = ['equipement', 'jour', 'heure_debut']

class Tarif(models.Model):

    """
    Définit le tarif horaire associés à un équipement pour une affiliation donnée.

    tarif_horaire    : coût horaire standard pour l’utilisation de l’équipement

    Attributs :
        equipement (Equipement)   : équipement concerné
        affiliation (Affiliation) : affiliation de l’usager (YourUniversity, McGill, UdeM…)
        tarif_horaire (Decimal)   : tarif standard en CAD/h

    Contraintes :
        - UniqueConstraint : empêche de définir deux tarifs différents
          pour le même couple (équipement, affiliation).
    """

    equipement = models.ForeignKey("Equipement", on_delete=models.CASCADE, related_name="tarifs")
    affiliation = models.ForeignKey("usager.Affiliation", on_delete=models.CASCADE)
    tarif_horaire = models.DecimalField(max_digits=6, decimal_places=2)

    class Meta:
        constraints = [
                models.UniqueConstraint(fields=['equipement', 'affiliation'], name='unique_tarif')
            ]
        verbose_name = "Tarif"
        verbose_name_plural = "Tarifs"

    def __str__(self):
        return f"{self.equipement.nom} - {self.affiliation.nom}: {self.tarif_horaire} CAD/h"

class TarifFormation(models.Model):
    """
    Définit le tarif FIXE de formation pour un couple (équipement, affiliation).

    Attributs :
        equipement (Equipement)   : équipement concerné
        affiliation (Affiliation) : affiliation de l’usager (YourUniversity, McGill, etc.)
        tarif_formation (Decimal) : prix fixe (CAD) facturé pour la formation

    Contraintes :
        - UniqueConstraint : un (équipement, affiliation) ne peut avoir qu’un seul tarif de formation.
    """
    equipement = models.ForeignKey("Equipement", on_delete=models.CASCADE, related_name="tarifs_formation")
    affiliation = models.ForeignKey("usager.Affiliation", on_delete=models.CASCADE)
    tarif_formation = models.DecimalField(max_digits=8, decimal_places=2, help_text="Prix fixe (CAD) pour la formation")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['equipement', 'affiliation'], name='unique_tarif_formation')
        ]
        verbose_name = "Tarif formation"
        verbose_name_plural = "Tarifs formation"

    def __str__(self):
        return f"{self.equipement.nom} - {self.affiliation.nom}: {self.tarif_formation} CAD (formation)"