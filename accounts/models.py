# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

"""
Module : user_profile.models
----------------------
Modèles liés à la gestion des usagers et de leurs rattachements.

Contenu :
- Role     : table de référence pour le rôle/fonction d'un user_profile.
- Affiliation  : organisme d'appartenance (YourUniversity, McGill, Industriel, etc.).
- Laboratory  : unité rattachée à une affiliation.
- UserProfile       : profil applicatif relié au User Django (auth).
- Invitation   : système d'invitation (email + équipements autorisés).

Remarques :
- La relation aux équipements autorisés (ManyToMany) vit côté UserProfile.
- La facturation peut utiliser plusieurs sources de rates (voir TODO ci-dessous).
"""

from django.db import models
from django.contrib.auth.models import User
from equipment.models import Equipment
from django.utils import timezone
from dateutil.relativedelta import relativedelta

# =====================================================================
#  Référentiels
# =====================================================================

class Role(models.Model):
    """
    Référentiel des fonctions/statuts d'un user_profile (étudiant, postdoc, etc.).
    Utilisé par le modèle UserProfile via une FK optionnelle.
    """
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Affiliation(models.Model):
    """
    Représente une affiliation (université, institut, entreprise…).

    Exemples : YourUniversity, McGill, Compagnie X.
    Une affiliation regroupe un ou plusieurs laboratoires.

    Champs :
        - name               : libellé unique
        - assistance_rate  : taux horaire d'assistance « par affiliation »
                              (peut coexister avec d'autres mécaniques de tarification)

    """
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Nom de l'affiliation (ex : YourUniversity, McGill)"
    )

    assistance_rate = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text="Taux horaire (en CAD) pour l'assistance technique"
    )

    def __str__(self):
        return self.name


class Laboratory(models.Model):
    """
    Représente un laboratoire (ou compagnie/unité) rattaché à une affiliation.

    Contrainte :
        - (name, affiliation) doit être unique pour éviter les doublons.
    """
    name = models.CharField(max_length=150, help_text="Nom du laboratoire")
    affiliation = models.ForeignKey(
        Affiliation,
        on_delete=models.CASCADE,
        related_name='laboratoires'
    )

    class Meta:
        unique_together = ('name', 'affiliation')  # Empêche doublons de labo pour une même affiliation

    def __str__(self):
        return f"{self.name} ({self.affiliation.name})"


# =====================================================================
#  UserProfiles & Invitations
# =====================================================================

class UserProfile(models.Model):
    """
    Profil applicatif étendu, lié 1–1 au `User` Django (authentification/permissions).

    Champs principaux :
        - user : lien OneToOne vers `auth.User`
        - first_name / name / email (email unique côté UserProfile)
        - fonction (FK -> Role, optionnelle)
        - affiliation (FK -> Affiliation, optionnelle)
        - laboratoire (FK -> Laboratory, optionnelle)
        - authorized_equipment (M2M -> Equipment)
        - is_active / is_platform_admin : flags applicatifs (différents des flags Django User)

    Notes :
        - `is_platform_admin` ici est un attribut *applicatif*. Il ne remplace pas `is_staff` / `is_superuser`
          du modèle `User`. On peut s'en servir pour l'UI ou des règles spécifiques.
        - La contrainte d'email unique côté UserProfile ne remplace pas l'unicité email côté User ;
          les deux sont utiles selon les écrans.
    """
    # (Option alternative possible : conserver des choices ; ici on utilise une table Role)
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
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='accounts'
    )

    first_name = models.CharField(max_length=30, help_text="Prénom de l'user_profile")
    name = models.CharField(max_length=30, help_text="Nom de famille de l'user_profile")

    email = models.EmailField(unique=True, help_text="Adresse email de l'user_profile (unique)")

    # Traçage de l'acceptation du règlement
    terms_accepted = models.BooleanField(default=False)
    terms_accepted_at = models.DateTimeField(null=True, blank=True)

    # Engagement acknowledgment publications (coché à l'inscription)
    registration_acknowledged = models.BooleanField(
        default=False,
        help_text="L'user_profile s'est engagé à mentionner la plateforme dans ses publications"
    )

    # Référentiels et rattachements
    fonction = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Role de l'user_profile"
    )
    affiliation = models.ForeignKey(
        Affiliation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Affiliation de l'user_profile"
    )
    laboratoire = models.ForeignKey(
        Laboratory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Laboratory de l'user_profile"
    )

    # Relation plusieurs-à-plusieurs vers les équipements autorisés
    authorized_equipment = models.ManyToManyField(
        'equipment.Equipment',
        blank=True,
        related_name='usagers_autorises'
    )

    # Flags d'état applicatifs
    is_active = models.BooleanField(default=False, help_text="Compte is_active ou désactivé")
    is_platform_admin = models.BooleanField(default=False, help_text="L'user_profile a les droits administratifs")


    # Date de création de l'user_profile pour vérification aux 5 ans
    activation_date = models.DateTimeField(default=timezone.now)        # point de départ
    last_reverification_date = models.DateTimeField(null=True, blank=True)  # maj quand un admin confirme

    # Date acceptation du reglement
    terms_accepted_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        # Affichage simple : « Prénom NOM »
        return f"{self.first_name} {self.name}"

    class Meta:
        ordering = ['name', 'first_name']
        verbose_name = "UserProfile"
        verbose_name_plural = "UserProfiles"

    @property
    def doit_reverification(self) -> bool:
        """         True si l'user_profile est is_active et que sa dernière (ou première) vérification remonte à ≥ 5 ans.
        """
        if not getattr(self, "is_active", True):
            return False
        ref = self.last_reverification_date or self.activation_date
        return ref <= (timezone.now() - relativedelta(years=5))

class Invitation(models.Model):
    email = models.EmailField()
    equipment_set = models.ManyToManyField("equipment.Equipment", blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)

    # Lien vers la réservation de formation (optionnel)
    reservation = models.ForeignKey(
        'booking.Reservation',  # ← chaîne au lieu d'import
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Réservation de formation liée à cette invitation"
    )


    # Date de validation de l'accès (optionnelle)
    validated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date à laquelle l'accès à l'équipement a été validé"
    )

    def est_lie_a_une_formation(self):
        return self.reservation and self.reservation.is_training

    def __str__(self):
        return f"Invitation pour {self.email}"

class TrainingInvitation(Invitation):
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
        ('equipment', 'Équipement'),
        ('evenement', 'Événement'),
        ('formation', 'Formation'),
        ('emploi', "Offre d'emploi"),
    ]

    title = models.CharField(max_length=200)
    content = models.TextField()
    category = models.CharField(
        max_length=20,
        choices=CATEGORIE_CHOICES,
        default='equipment',
        help_text="Catégorie de l'actualité"
    )
    published_at = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-published_at']
        verbose_name = "Actualité"
        verbose_name_plural = "Actualités"
