# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

"""
Module : usager.forms
---------------------
Définit les formulaires liés à la gestion des usagers :
- Création / modification d'usager (UsagerForm, UsagerAdminForm)
- Inscription en autonomie (InscriptionForm)
- Connexion par email (EmailLoginForm)
- Gestion des invitations (InvitationForm)
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Fonction, Usager, Affiliation, Laboratoire, Invitation
from django.contrib.auth import authenticate
from equipements.models import Equipement
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

# === Formulaire usager standard ===
class UsagerForm(forms.ModelForm):
    """
    Formulaire pour créer ou modifier un usager.

    Champs spécifiques :
    - affiliation : choix obligatoire (liste complète).
    - laboratoire : filtré dynamiquement selon l'affiliation choisie.
    """

    affiliation = forms.ModelChoiceField(
        queryset=Affiliation.objects.all(),
        required=True,
        label="Affiliation",
        help_text="Choisissez l'affiliation de l'usager."
    )
    laboratoire = forms.ModelChoiceField(
        queryset=Laboratoire.objects.none(),
        required=True,
        label="Laboratoire",
        help_text="Choisissez le laboratoire correspondant à l'affiliation."
    )

    class Meta:
        model = Usager
        fields = [
            "prenom", "nom", "courriel",
            "fonction", "affiliation", "laboratoire",
            "equipements_autorises",
            "est_actif", "est_admin",
            "compte_utilisateur",
        ]

    def __init__(self, *args, **kwargs):
        """Filtre les laboratoires selon l'affiliation déjà choisie ou l'instance."""
        super().__init__(*args, **kwargs)
        self.fields['laboratoire'].label = "Laboratoire / Compagnie"

        if 'affiliation' in self.data:
            # Cas formulaire soumis : on filtre en fonction de la valeur choisie
            try:
                affiliation_id = int(self.data.get('affiliation'))
                self.fields['laboratoire'].queryset = Laboratoire.objects.filter(
                    affiliation_id=affiliation_id
                ).order_by('nom')
            except (ValueError, TypeError):
                self.fields['laboratoire'].queryset = Laboratoire.objects.none()
        elif self.instance.pk and self.instance.affiliation:
            # Cas édition : on filtre avec l'affiliation de l'usager existant
            self.fields['laboratoire'].queryset = Laboratoire.objects.filter(
                affiliation=self.instance.affiliation
            ).order_by('nom')
        else:
            # Cas création : pas encore d'affiliation → labo vide
            self.fields['laboratoire'].queryset = Laboratoire.objects.none()

    def clean_courriel(self):
        """
        Vérifie l'unicité du courriel :
        - pas déjà utilisé dans un autre Usager
        - existe dans la table User (lié au système d'authentification Django)
        """
        courriel = self.cleaned_data.get('courriel')

        if Usager.objects.exclude(pk=self.instance.pk).filter(courriel__iexact=courriel).exists():
            raise ValidationError("Cette adresse courriel est déjà utilisée par un autre usager.")

        if not User.objects.filter(email__iexact=courriel).exists():
            raise ValidationError("Aucun compte utilisateur associé à cette adresse courriel.")

        return courriel

    def clean(self):
        """Validation croisée : cohérence affiliation ↔ laboratoire."""
        cleaned_data = super().clean()
        affiliation = cleaned_data.get('affiliation')
        laboratoire = cleaned_data.get('laboratoire')

        if affiliation and laboratoire and laboratoire.affiliation != affiliation:
            raise ValidationError("Le laboratoire sélectionné ne correspond pas à l'affiliation choisie.")
        return cleaned_data


# === Formulaire admin (utilisé dans Django admin) ===
class UsagerAdminForm(forms.ModelForm):
    """
    Version admin du formulaire usager.
    Permet de limiter la liste des `compte_utilisateur` disponibles
    aux Users non encore liés à un Usager.
    """
    class Meta:
        model = Usager
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'compte_utilisateur' in self.fields:
            users_utilises = Usager.objects.exclude(
                pk=self.instance.pk if self.instance and self.instance.pk else None
            ).values_list('compte_utilisateur__id', flat=True)

            self.fields['compte_utilisateur'].queryset = User.objects.exclude(id__in=users_utilises)


# === Formulaire d'inscription publique ===
class InscriptionForm(forms.ModelForm):
    """
    Permet à un nouvel usager de s'inscrire :
    - crée un User désactivé + un Usager lié
    - vérifie la confirmation du mot de passe
    - peut pré-remplir le champ email via l'URL (?courriel=...)
    """
    email = forms.EmailField(label="Adresse courriel")
    password = forms.CharField(label="Mot de passe", widget=forms.PasswordInput)
    password_confirmation = forms.CharField(label="Confirmation du mot de passe", widget=forms.PasswordInput)
    acknowledgment_inscription = forms.BooleanField(
        required=True,
        label="Je m'engage à inclure la mention suivante dans mes publications scientifiques issues de "
              "données acquises sur la plateforme ou d'un soutien fourni par la plateforme :",
    )

    class Meta:
        model = Usager
        fields = ['prenom', 'nom', 'fonction', 'affiliation', 'laboratoire']

    def __init__(self, *args, **kwargs):
        initial = kwargs.get("initial", {})
        request = kwargs.pop("request", None)
        language = kwargs.pop("language", "fr")

        # Préremplissage depuis paramètre GET (?courriel=)
        if request:
            courriel = request.GET.get("courriel")
            if courriel:
                initial["email"] = courriel
        kwargs["initial"] = initial
        super().__init__(*args, **kwargs)

        if language == 'en':
            self.fields['email'].label = "Email Address"
            self.fields['password'].label = "Password"
            self.fields['password_confirmation'].label = "Confirm Password"
            self.fields['prenom'].label = "First Name"
            self.fields['nom'].label = "Last Name"
            self.fields['fonction'].label = "Position"
            self.fields['affiliation'].label = "Affiliation"
            self.fields['laboratoire'].label = "Laboratory / Company"
            self.fields['acknowledgment_inscription'].label = (
                "I commit to including the following acknowledgment in my scientific publications "
                "resulting from data acquired on the platform or from support provided by the platform:"
            )
        else:
            self.fields['laboratoire'].label = "Laboratoire / Compagnie"

        if Fonction.objects.exists():
            self.fields['fonction'].queryset = Fonction.objects.all()
        if Affiliation.objects.exists():
            self.fields['affiliation'].queryset = Affiliation.objects.all()
        if Laboratoire.objects.exists():
            self.fields['laboratoire'].queryset = Laboratoire.objects.all()

    def clean(self):
        """
        Validation du formulaire :
        - Vérifie la concordance des mots de passe.
        - Vérifie qu'aucun profil usager complet n'existe déjà pour ce courriel.
          (Un Usager "vide" créé automatiquement par le signal est toléré.)
        """
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirmation = cleaned_data.get("password_confirmation")
        email = cleaned_data.get("email")

        # 1. Vérification mots de passe
        if password and confirmation and password != confirmation:
            self.add_error('password_confirmation', "Les mots de passe ne correspondent pas.")

        # 2. Vérification usager existant
        if email:
            usager = Usager.objects.filter(courriel__iexact=email).first()
            if usager:
                # On considère le profil "déjà complété" si prénom ET nom non vides
                if usager.prenom or usager.nom:
                    self.add_error("email", "Un usager avec cette adresse a déjà complété son inscription.")

        return cleaned_data


    def save(self, commit=True):
        """
        Crée ou récupère le User associé, puis complète l'Usager déjà
        créé automatiquement par le signal post_save (creer_usager_associe).

        - Si le User existe déjà (via invitation ou admin), on le réutilise.
        - Si c'est un nouveau User, le signal crée automatiquement un Usager
          lié avec les infos minimales (nom, prénom, courriel vides).
        - Dans tous les cas, on complète / met à jour l'Usager ici.
        """
        email = self.cleaned_data['email']
        password = self.cleaned_data['password']

        # 1) Récupération ou création du User
        user, created = User.objects.get_or_create(
            username=email,
            defaults={
                'email': email,
                'is_active': False
            }
        )

        # Définir / mettre à jour le mot de passe
        user.set_password(password)
        if commit:
            user.save()

        # 2) Récupération de l'Usager lié (créé automatiquement par le signal)
        usager = getattr(user, 'usager', None)
        if usager is None:
            # Normalement le signal a déjà créé un Usager.
            # Ce fallback est là juste par sécurité.
            usager = Usager(compte_utilisateur=user, courriel=email)

        # 3) Compléter / mettre à jour le profil Usager
        usager.nom = self.cleaned_data['nom']
        usager.prenom = self.cleaned_data['prenom']
        usager.fonction = self.cleaned_data['fonction']
        usager.affiliation = self.cleaned_data['affiliation']
        usager.laboratoire = self.cleaned_data['laboratoire']
        usager.courriel = email
        usager.acknowledgment_inscription = self.cleaned_data.get('acknowledgment_inscription', False)

        if commit:
            usager.save()

            # 4) Si une invitation existe, rattacher les équipements autorisés
            invitation = Invitation.objects.filter(courriel__iexact=email).order_by('-date_envoi').first()
            if invitation and invitation.equipements.exists():
                usager.equipements_autorises.set(invitation.equipements.all())
                usager.save()

        # 5) Retourner le User (comme attendu par la vue d'inscription)
        return user


# === Formulaire de connexion par email ===
class EmailLoginForm(forms.Form):
    """
    Formulaire d'authentification basé sur email + mot de passe.
    Utilise le backend `EmailAuthBackend` pour l'authentification.
    """
    email = forms.EmailField(label="Adresse courriel")
    password = forms.CharField(label="Mot de passe", widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        """Vérifie l'authentification via `authenticate`."""
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')

        if email and password:
            self.user = authenticate(username=email, password=password)
            if self.user is None:
                raise ValidationError("Adresse courriel ou mot de passe invalide.")
        return self.cleaned_data

    def get_user(self):
        """Retourne l'utilisateur authentifié (ou None)."""
        return getattr(self, 'user', None)


# === Formulaire d'invitation ===
class InvitationForm(forms.ModelForm):
    """
    Permet d'inviter un nouvel usager :
    - saisie d'un email
    - choix des équipements autorisés (via cases à cocher)
    """
    class Meta:
        model = Invitation
        fields = ['courriel', 'equipements']
        widgets = {
            'equipements': forms.CheckboxSelectMultiple,
        }

    def save(self, commit=True):
        invitation = super().save(commit=False)
        if commit:
            invitation.save()
            self.save_m2m()  # important pour ManyToMany
        return invitation
