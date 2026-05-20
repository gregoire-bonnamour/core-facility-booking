# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NoCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

"""
Module: user_profile.forms
---------------------
Définit les formulaires liés à la gestion des user_profiles :
- Création / modification d'user_profile (UserProfileForm, UserProfileAdminForm)
- Inscription en autonomie (RegistrationForm)
- Connexion par email (EmailLoginForm)
- Gestion des invitations (InvitationForm)
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Role, UserProfile, Affiliation, Laboratory, Invitation
from django.contrib.auth import authenticate
from equipment.models import Equipment
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

# === Formulaire user_profile standard ===
class UserProfileForm(forms.ModelForm):
    """
    Formulaire pour créer ou modifier un user_profile.

    Champs spécifiques :
    - affiliation : choix obligatoire (liste complète).
    - laboratory : filtré dynamiquement selon l'affiliation choisie.
    """

    affiliation = forms.ModelChoiceField(
        queryset=Affiliation.objects.all(),
        required=True,
        label="Affiliation",
        help_text="Choisissez l'affiliation de l'user_profile."
    )
    laboratory = forms.ModelChoiceField(
        queryset=Laboratory.objects.none(),
        required=True,
        label="Laboratory",
        help_text="Choisissez le laboratory correspondant à l'affiliation."
    )

    class Meta:
        model = UserProfile
        fields = [
            "first_name", "name", "email",
            "role", "affiliation", "laboratory",
            "authorized_equipment",
            "is_active", "is_platform_admin",
            "user",
        ]

    def __init__(self, *args, **kwargs):
        """Filtre les laboratories selon l'affiliation déjà choisie ou l'instance."""
        super().__init__(*args, **kwargs)
        self.fields['laboratory'].label = "Laboratory / Compagnie"

        if 'affiliation' in self.data:
            # Cas formulaire soumis : on filtre en role de la valeur choisie
            try:
                affiliation_id = int(self.data.get('affiliation'))
                self.fields['laboratory'].queryset = Laboratory.objects.filter(
                    affiliation_id=affiliation_id
                ).order_by('name')
            except (ValueError, TypeError):
                self.fields['laboratory'].queryset = Laboratory.objects.none()
        elif self.instance.pk and self.instance.affiliation:
            # Cas édition : on filtre avec l'affiliation de l'user_profile existant
            self.fields['laboratory'].queryset = Laboratory.objects.filter(
                affiliation=self.instance.affiliation
            ).order_by('name')
        else:
            # Cas création : pas encore d'affiliation → lab vide
            self.fields['laboratory'].queryset = Laboratory.objects.none()

    def clean_email(self):
        """
        Vérifie l'unicité du email :
        - pas déjà utilisé dans un autre UserProfile
        - existe dans la table User (lié au système d'authentification Django)
        """
        email = self.cleaned_data.get('email')

        if UserProfile.objects.exclude(pk=self.instance.pk).filter(email__iexact=email).exists():
            raise ValidationError("Cette adresse email est déjà utilisée par un autre user_profile.")

        if not User.objects.filter(email__iexact=email).exists():
            raise ValidationError("No compte utilisateur associé à cette adresse email.")

        return email

    def clean(self):
        """Validation croisée : cohérence affiliation ↔ laboratory."""
        cleaned_data = super().clean()
        affiliation = cleaned_data.get('affiliation')
        laboratory = cleaned_data.get('laboratory')

        if affiliation and laboratory and laboratory.affiliation != affiliation:
            raise ValidationError("Le laboratory sélectionné ne correspond pas à l'affiliation choisie.")
        return cleaned_data


# === Formulaire admin (utilisé dans Django admin) ===
class UserProfileAdminForm(forms.ModelForm):
    """
    Version admin du formulaire user_profile.
    Permet de limiter la liste des `user` disponibles
    aux Users non encore liés à un UserProfile.
    """
    class Meta:
        model = UserProfile
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'user' in self.fields:
            users_utilises = UserProfile.objects.exclude(
                pk=self.instance.pk if self.instance and self.instance.pk else None
            ).values_list('user__id', flat=True)

            self.fields['user'].queryset = User.objects.exclude(id__in=users_utilises)


# === Formulaire d'inscription publique ===
class RegistrationForm(forms.ModelForm):
    """
    Permet à un nouvel user_profile de s'inscrire :
    - crée un User désactivé + un UserProfile lié
    - vérifie la confirmation du mot de passe
    - peut pré-remplir le champ email via l'URL (?email=...)
    """
    email = forms.EmailField(label="Adresse email")
    password = forms.CharField(label="Mot de passe", widget=forms.PasswordInput)
    password_confirmation = forms.CharField(label="Confirmation du mot de passe", widget=forms.PasswordInput)
    registration_acknowledged = forms.BooleanField(
        required=True,
        label="Je m'engage à inclure la mention suivante dans mes publications scientifiques issues de "
              "données acquises sur la plateforme ou d'un soutien fourni par la plateforme :",
    )

    class Meta:
        model = UserProfile
        fields = ['first_name', 'name', 'role', 'affiliation', 'laboratory']

    def __init__(self, *args, **kwargs):
        initial = kwargs.get("initial", {})
        request = kwargs.pop("request", None)
        language = kwargs.pop("language", "fr")

        # Préremplissage depuis paramètre GET (?email=)
        if request:
            email = request.GET.get("email")
            if email:
                initial["email"] = email
        kwargs["initial"] = initial
        super().__init__(*args, **kwargs)

        if language == 'en':
            self.fields['email'].label = "Email Address"
            self.fields['password'].label = "Password"
            self.fields['password_confirmation'].label = "Confirm Password"
            self.fields['first_name'].label = "First Name"
            self.fields['name'].label = "Last Name"
            self.fields['role'].label = "Position"
            self.fields['affiliation'].label = "Affiliation"
            self.fields['laboratory'].label = "Laboratory / Company"
            self.fields['registration_acknowledged'].label = (
                "I commit to including the following acknowledgment in my scientific publications "
                "resulting from data acquired on the platform or from support provided by the platform:"
            )
        else:
            self.fields['laboratory'].label = "Laboratory / Compagnie"

        if Role.objects.exists():
            self.fields['role'].queryset = Role.objects.all()
        if Affiliation.objects.exists():
            self.fields['affiliation'].queryset = Affiliation.objects.all()
        if Laboratory.objects.exists():
            self.fields['laboratory'].queryset = Laboratory.objects.all()

    def clean(self):
        """
        Validation du formulaire :
        - Vérifie la concordance des mots de passe.
        - Vérifie qu'no profil user_profile complet n'existe déjà pour ce email.
          (Un UserProfile "vide" créé automatiquement par le signal est toléré.)
        """
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirmation = cleaned_data.get("password_confirmation")
        email = cleaned_data.get("email")

        # 1. Vérification mots de passe
        if password and confirmation and password != confirmation:
            self.add_error('password_confirmation', "Les mots de passe ne correspondent pas.")

        # 2. Vérification user_profile existant
        if email:
            user_profile = UserProfile.objects.filter(email__iexact=email).first()
            if user_profile:
                # On considère le profil "déjà complété" si prénom ET name non vides
                if user_profile.first_name or user_profile.name:
                    self.add_error("email", "Un user_profile avec cette adresse a déjà complété son inscription.")

        return cleaned_data


    def save(self, commit=True):
        """
        Crée ou récupère le User associé, puis complète l'UserProfile déjà
        créé automatiquement par le signal post_save (creer_usager_associe).

        - Si le User existe déjà (via invitation ou admin), on le réutilise.
        - Si c'est un nouveau User, le signal crée automatiquement un UserProfile
          lié avec les infos minimales (name, prénom, email vides).
        - Dans tous les cas, on complète / met à day_of_week l'UserProfile ici.
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

        # Définir / mettre à day_of_week le mot de passe
        user.set_password(password)
        if commit:
            user.save()

        # 2) Récupération de l'UserProfile lié (créé automatiquement par le signal)
        user_profile = getattr(user, 'accounts', None)
        if user_profile is None:
            # Normalement le signal a déjà créé un UserProfile.
            # Ce fallback est là juste par sécurité.
            user_profile = UserProfile(user=user, email=email)

        # 3) Compléter / mettre à day_of_week le profil UserProfile
        user_profile.name = self.cleaned_data['name']
        user_profile.first_name = self.cleaned_data['first_name']
        user_profile.role = self.cleaned_data['role']
        user_profile.affiliation = self.cleaned_data['affiliation']
        user_profile.laboratory = self.cleaned_data['laboratory']
        user_profile.email = email
        user_profile.registration_acknowledged = self.cleaned_data.get('registration_acknowledged', False)

        if commit:
            user_profile.save()

            # 4) Si une invitation existe, rattacher les équipements autorisés
            invitation = Invitation.objects.filter(email__iexact=email).order_by('-sent_at').first()
            if invitation and invitation.equipment_set.exists():
                user_profile.authorized_equipment.set(invitation.equipment_set.all())
                user_profile.save()

        # 5) Returnsr le User (comme attendu par la vue d'inscription)
        return user


# === Formulaire de connexion par email ===
class EmailLoginForm(forms.Form):
    """
    Formulaire d'authentification basé sur email + mot de passe.
    Utilise le backend `EmailAuthBackend` pour l'authentification.
    """
    email = forms.EmailField(label="Adresse email")
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
                raise ValidationError("Adresse email ou mot de passe invalide.")
        return self.cleaned_data

    def get_user(self):
        """Returns l'utilisateur authentifié (ou None)."""
        return getattr(self, 'user', None)


# === Formulaire d'invitation ===
class InvitationForm(forms.ModelForm):
    """
    Permet d'inviter un nouvel user_profile :
    - saisie d'un email
    - choix des équipements autorisés (via cases à cocher)
    """
    class Meta:
        model = Invitation
        fields = ['email', 'equipment_set']
        widgets = {
            'equipment_set': forms.CheckboxSelectMultiple,
        }

    def save(self, commit=True):
        invitation = super().save(commit=False)
        if commit:
            invitation.save()
            self.save_m2m()  # important pour ManyToMany
        return invitation
