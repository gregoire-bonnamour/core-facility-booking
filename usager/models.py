# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

"""
Module : usager.models
----------------------
Modèles liés à la gestion des usagers et de leurs rattachements.

Contenu :
- Fonction     : table de référence pour le rôle/fonction d'un usager.
- Affiliation  : organisme d'appartenance (YourUniversity, McGill, Industriel, etc.).
- Laboratoire  : unité rattachée à une affiliation.
- Usager       : profil applicatif relié au User Django (auth).
- Invitation   : système d'invitation (email + équipements autorisés).

Remarques :
- La relation aux équipements autorisés (ManyToMany) vit côté Usager.
- La facturation peut utiliser plusieurs sources de tarifs (voir TODO ci-dessous).
"""

from django.db import models
from django.contrib.auth.models import User
from equipements.models import Equipement
from django.utils import timezone
from dateutil.relativedelta import relativedelta

# =====================================================================
#  Référentiels
# =====================================================================

class Fonction(models.Model):
    """
    Référentiel des fonctions/statuts d'un usager (étudiant, postdoc, etc.).
    Utilisé par le modèle Usager via une FK optionnelle.
    """
    nom = models.CharField(max_length=100)

    def __str__(self):
        return self.nom


class Affiliation(models.Model):
    """
    Représente une affiliation (université, institut, entreprise…).

    Exemples : YourUniversity, McGill, Compagnie X.
    Une affiliation regroupe un ou plusieurs laboratoires.

    Champs :
        - nom               : libellé unique
        - tarif_assistance  : taux horaire d'assistance « par affiliation »
                              (peut coexister avec d'autres mécaniques de tarification)

    """
    nom = models.CharField(
        max_length=100,
        unique=True,
        help_text="Nom de l'affiliation (ex : YourUniversity, McGill)"
    )

    tarif_assistance = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text="Taux horaire (en CAD) pour l'assistance technique"
    )

    def __str__(self):
        return self.nom


class Laboratoire(models.Model):
    """
    Représente un laboratoire (ou compagnie/unité) rattaché à une affiliation.

    Contrainte :
        - (nom, affiliation) doit être unique pour éviter les doublons.
    """
    nom = models.CharField(max_length=150, help_text="Nom du laboratoire")
    affiliation = models.ForeignKey(
        Affiliation,
        on_delete=models.CASCADE,
        related_name='laboratoires'
    )

    class Meta:
        unique_together = ('nom', 'affiliation')  # Empêche doublons de labo pour une même affiliation

    def __str__(self):
        return f"{self.nom} ({self.affiliation.nom})"


# =====================================================================
#  Usagers & Invitations
# =====================================================================

class Usager(models.Model):
    """
    Profil applicatif étendu, lié 1–1 au `User` Django (authentification/permissions).

    Champs principaux :
        - compte_utilisateur : lien OneToOne vers `auth.User`
        - prenom / nom / courriel (email unique côté Usager)
        - fonction (FK -> Fonction, optionnelle)
        - affiliation (FK -> Affiliation, optionnelle)
        - laboratoire (FK -> Laboratoire, optionnelle)
        - equipements_autorises (M2M -> Equipement)
        - est_actif / est_admin : flags applicatifs (différents des flags Django User)

    Notes :
        - `est_admin` ici est un attribut *applicatif*. Il ne remplace pas `is_staff` / `is_superuser`
          du modèle `User`. On peut s'en servir pour l'UI ou des règles spécifiques.
        - La contrainte d'email unique côté Usager ne remplace pas l'unicité email côté User ;
          les deux sont utiles selon les écrans.
    """
    # (Option alternative possible : conserver des choices ; ici on utilise une table Fonction)
    FONCTION_CHOICES = [
        ('etudiant1', "Étudiant 1er cycle"),
        ('etudiant2', "Étudiant 2e cycle"),
        ('etudiant3', "Étudiant 3e cycle"),
        ('postdoc', "Post-doc"),
        ('professionnel', "Professionnel"),
        ('chercheur', "Chercheur"),
        ('autre', "Autre"),
    ]

    # Lien 1-1 avec le compte User Django classique (authentification, permissions, etc.)
    compte_utilisateur = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='usager'
    )

    prenom = models.CharField(max_length=30, help_text="Prénom de l'usager")
    nom = models.CharField(max_length=30, help_text="Nom de famille de l'usager")

    courriel = models.EmailField(unique=True, help_text="Adresse courriel de l'usager (unique)")

    # Traçage de l'acceptation du règlement
    reglement_accepte = models.BooleanField(default=False)
    reglement_accepte_at = models.DateTimeField(null=True, blank=True)

    # Engagement acknowledgment publications (coché à l'inscription)
    acknowledgment_inscription = models.BooleanField(
        default=False,
        help_text="L'usager s'est engagé à mentionner la plateforme dans ses publications"
    )

    # Référentiels et rattachements
    fonction = models.ForeignKey(
        Fonction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Fonction de l'usager"
    )
    affiliation = models.ForeignKey(
        Affiliation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Affiliation de l'usager"
    )
    laboratoire = models.ForeignKey(
        Laboratoire,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Laboratoire de l'usager"
    )

    # Relation plusieurs-à-plusieurs vers les équipements autorisés
    equipements_autorises = models.ManyToManyField(
        'equipements.Equipement',
        blank=True,
        related_name='usagers_autorises'
    )

    # Flags d'état applicatifs
    est_actif = models.BooleanField(default=False, help_text="Compte actif ou désactivé")
    est_admin = models.BooleanField(default=False, help_text="L'usager a les droits administratifs")


    # Date de création de l'usager pour vérification aux 5 ans
    date_activation = models.DateTimeField(default=timezone.now)        # point de départ
    date_derniere_reverification = models.DateTimeField(null=True, blank=True)  # maj quand un admin confirme

    # Date acceptation du reglement
    date_acceptation_reglement = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        # Affichage simple : « Prénom NOM »
        return f"{self.prenom} {self.nom}"

    class Meta:
        ordering = ['nom', 'prenom']
        verbose_name = "Usager"
        verbose_name_plural = "Usagers"

    @property
    def doit_reverification(self) -> bool:
        """         True si l'usager est actif et que sa dernière (ou première) vérification remonte à ≥ 5 ans.
        """
        if not getattr(self, "est_actif", True):
            return False
        ref = self.date_derniere_reverification or self.date_activation
        return ref <= (timezone.now() - relativedelta(years=5))

class Invitation(models.Model):
    courriel = models.EmailField()
    equipements = models.ManyToManyField("equipements.Equipement", blank=True)
    date_envoi = models.DateTimeField(auto_now_add=True)

    # Lien vers la réservation de formation (optionnel)
    reservation = models.ForeignKey(
        'reserv.Reservation',  # ← chaîne au lieu d'import
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Réservation de formation liée à cette invitation"
    )


    # Date de validation de l'accès (optionnelle)
    date_validation = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date à laquelle l'accès à l'équipement a été validé"
    )

    def est_lie_a_une_formation(self):
        return self.reservation and self.reservation.est_formation

    def __str__(self):
        return f"Invitation pour {self.courriel}"

class InvitationFormation(Invitation):
    """
    Proxy pour exposer un lien 'Validation des formations'
    dans l'admin, sans ajouter de nouvelle table.
    """
    class Meta:
        proxy = True
        verbose_name = "Validation des formations"
        verbose_name_plural = "Validation des formations"

class News(models.Model):
    CATEGORIE_CHOICES = [
        ('equipement', 'Équipement'),
        ('evenement', 'Événement'),
        ('formation', 'Formation'),
        ('emploi', "Offre d'emploi"),
    ]

    titre = models.CharField(max_length=200)
    contenu = models.TextField()
    categorie = models.CharField(
        max_length=20,
        choices=CATEGORIE_CHOICES,
        default='equipement',
        help_text="Catégorie de l'actualité"
    )
    date_publication = models.DateTimeField(default=timezone.now)
    actif = models.BooleanField(default=True)

    class Meta:
        ordering = ['-date_publication']
        verbose_name = "Actualité"
        verbose_name_plural = "Actualités"
