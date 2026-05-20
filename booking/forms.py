# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

"""
Module : reserv.forms
---------------------
Formulaires lies aux reservations.

Deux formulaires principaux :
- ReservationForm             : creation de reservation avec toutes les regles metier.
- ReservationModificationForm : modification, incluant l'assistance.

Regles implementees :
- Regles de base (dates futures, coherence debut/fin, pas de chevauchement).
- Gestion des demandes exceptionnelles (bypass des regles optionnelles).
- Validation par rapport aux creneaux autorises.
- Validation par rapport aux plages limites (duree max par usager).
"""

from django import forms
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import Reservation
from equipment.models import Creneau, PlageLimite
from datetime import datetime, timedelta, time

HOUR_CHOICES = [(f"{h:02d}", f"{h:02d}") for h in range(24)]
MINUTE_CHOICES = [(f"{m:02d}", f"{m:02d}") for m in range(0, 60, 10)]

def generate_time_choices():
    choices = []
    for h in range(0, 24):
        for m in range(0, 60, 10):  # pas de 10 minutes
            t = f"{h:02d}:{m:02d}"
            choices.append((t, t))
    return choices

class ReservationForm(forms.ModelForm):
    # Champs virtuels pour l'UI
    heure_debut_h = forms.ChoiceField(choices=HOUR_CHOICES, label="Heure debut")
    minute_debut_m = forms.ChoiceField(choices=MINUTE_CHOICES, label="Minutes debut")
    heure_fin_h = forms.ChoiceField(choices=HOUR_CHOICES, label="Heure fin")
    minute_fin_m = forms.ChoiceField(choices=MINUTE_CHOICES, label="Minutes fin")

    # Champs virtuels (ne se sauvegardent PAS dans la DB)
    # Ils servent uniquement a l'interface pour les admins
    type_reservation_maintenance = forms.BooleanField(
        required=False,
        label="Reservation Maintenance",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        help_text="La reservation sera attribuee a l'usager systeme 'Maintenance'"
    )
    type_reservation_enseignement = forms.BooleanField(
        required=False,
        label="Reservation Enseignement",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        help_text="La reservation sera attribuee a l'usager systeme 'Enseignement'"
    )

    date_debut = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}, format="%Y-%m-%d"),
        input_formats=["%Y-%m-%d"],
        required=True,
        label="Debut :",
    )
    date_fin = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}, format="%Y-%m-%d"),
        input_formats=["%Y-%m-%d"],
        required=True,
        label="Fin :",
    )

    class Meta:
        model = Reservation
        fields = [
            "date_debut",
            "date_fin",
            "heure_debut_h", "minute_debut_m",
            "heure_fin_h", "minute_fin_m",
            "demande_exception",
            "justification",
            "est_formation",
            "courriels_formes",
            "assistance",
            "duree_assistance_minutes",
        ]
        widgets = {
            "date_debut": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "date_fin": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "demande_exception": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "justification": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "est_formation": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "courriels_formes": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }
        help_texts = {
            "est_formation": "Cochez si cette reservation est une formation (facturation au tarif fixe).",
            "courriels_formes": "Saisissez les courriels des participants (separes par des virgules, points-virgules ou sauts de ligne).",
        }

    def __init__(self, *args, **kwargs):
        self.usager = kwargs.pop('accounts', None)
        self.equipement = kwargs.pop('equipement', None)
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        # Champs non obligatoires
        self.fields['justification'].required = False
        self.fields['courriels_formes'].required = False
        self.fields['duree_assistance_minutes'].required = False
        self.fields['duree_assistance_minutes'].widget = forms.NumberInput(attrs={'min': 0, 'step': 5})

        # Masquer certains champs pour les non-admin
        is_admin = False
        if self.request and self.request.user.is_authenticated:
            is_admin = self.request.user.is_staff or (hasattr(self.request.user, 'accounts') and self.request.user.usager.est_admin)

        if not is_admin:
            self.fields['est_formation'].widget = forms.HiddenInput()
            self.fields['est_formation'].initial = False
            self.fields['courriels_formes'].widget = forms.HiddenInput()
            self.fields['type_reservation_maintenance'].widget = forms.HiddenInput()
            self.fields['type_reservation_enseignement'].widget = forms.HiddenInput()

    def clean(self):
        cleaned_data = super().clean()

        date_debut = cleaned_data.get("date_debut")
        date_fin = cleaned_data.get("date_fin")
        demande_exception = cleaned_data.get("demande_exception")
        justification = cleaned_data.get("justification")

        # Recomposition des heures
        h_d = cleaned_data.get("heure_debut_h")
        m_d = cleaned_data.get("minute_debut_m")
        h_f = cleaned_data.get("heure_fin_h")
        m_f = cleaned_data.get("minute_fin_m")

        heure_debut = time(int(h_d), int(m_d)) if h_d and m_d else None
        heure_fin = time(int(h_f), int(m_f)) if h_f and m_f else None

        # Injecter dans cleaned_data -> correspondance avec le modele
        cleaned_data["heure_debut"] = heure_debut
        cleaned_data["heure_fin"] = heure_fin

        if not date_debut or not date_fin or not heure_debut or not heure_fin:
            return cleaned_data  # stop si donnees incompletes

        dt_debut = timezone.make_aware(datetime.combine(date_debut, heure_debut))
        dt_fin = timezone.make_aware(datetime.combine(date_fin, heure_fin))

        # 1. Reservation future
        if dt_debut < timezone.now():
            self.add_error("date_debut", "La reservation doit commencer dans le futur.")

        # 2. Debut < fin
        if dt_debut >= dt_fin:
            self.add_error("heure_debut_h", "L'heure de debut doit etre avant l'heure de fin.")
            self.add_error("heure_fin_h", "L'heure de fin doit etre apres l'heure de debut.")

        # 3. Chevauchement
        if self.equipement:
            conflits = (
                Reservation.objects
                .filter(equipement=self.equipement)
                .exclude(pk=self.instance.pk)
                .exclude(statut__in=['annulee', 'passee'])
            )
            for r in conflits:
                r_debut = timezone.make_aware(datetime.combine(r.date_debut, r.heure_debut))
                r_fin = timezone.make_aware(datetime.combine(r.date_fin, r.heure_fin))
                if dt_debut < r_fin and dt_fin > r_debut:
                    raise ValidationError(
                        f"Chevauche une autre reservation : {r.date_debut} {r.heure_debut}-{r.heure_fin}"
                    )

        # 4. Duree maximale globale (parametre equipement)
        duree_totale = dt_fin - dt_debut
        if self.equipement and not demande_exception:
            duree_max = getattr(self.equipement, "duree_max_heures", 72)
            if duree_totale > timedelta(hours=duree_max):
                raise ValidationError(
                    f"La reservation depasse la duree maximale autorisee de {duree_max}h "
                    f"pour cet equipement (sauf demande exceptionnelle)."
                )

        # 5. Exception -> justification obligatoire
        if demande_exception and not justification:
            self.add_error("justification", "Veuillez expliquer la demande d'exception.")

        # Validation Assistance : Duree obligatoire si coche
        assistance = cleaned_data.get("assistance")
        duree_assistance = cleaned_data.get("duree_assistance_minutes")
        if assistance and (duree_assistance is None or duree_assistance <= 0):
            self.add_error("duree_assistance_minutes", "La duree d'assistance est obligatoire si cette option est cochee.")

        # Validation : Maintenance et Enseignement sont mutuellement exclusifs
        type_maint = cleaned_data.get("type_reservation_maintenance", False)
        type_enseign = cleaned_data.get("type_reservation_enseignement", False)
        if type_maint and type_enseign:
            raise ValidationError(
                "Une reservation ne peut pas etre a la fois Maintenance et Enseignement. "
                "Veuillez ne cocher qu'une seule option."
            )

        if demande_exception:
            return cleaned_data  # on bypass les regles optionnelles (creneaux, plages)

        # 6. Respect des creneaux autorises
        creneaux = Creneau.objects.filter(equipement=self.equipement, jour=date_debut.weekday())
        if creneaux.exists():
            touche, respecte = False, False
            for c in creneaux:
                if (heure_debut < c.heure_fin and heure_fin > c.heure_debut):
                    touche = True
                    if c.heure_debut <= heure_debut and c.heure_fin >= heure_fin:
                        respecte = True
                        break
            if touche and not respecte:
                raise ValidationError("Reservation hors des creneaux autorises pour ce jour.")

        # 7. Limites cumulees
        plages = PlageLimite.objects.filter(equipement=self.equipement, jour=date_debut.weekday())
        for plage in plages:
            if plage.heure_debut <= heure_debut < plage.heure_fin or plage.heure_debut < heure_fin <= plage.heure_fin:
                total = timedelta()
                reservations = Reservation.objects.filter(
                    usager=self.usager,
                    equipement=self.equipement,
                    date_debut=date_debut,
                    statut__in=['a_venir', 'en_attente'],
                    heure_debut__lt=plage.heure_fin,
                    heure_fin__gt=plage.heure_debut,
                )
                if self.instance.pk:
                    reservations = reservations.exclude(pk=self.instance.pk)

                for r in reservations:
                    total += datetime.combine(date_debut, r.heure_fin) - datetime.combine(date_debut, r.heure_debut)

                total += dt_fin - dt_debut
                if total > timedelta(minutes=plage.duree_max_minutes):
                    raise ValidationError(
                        f"Duree totale ({total}) > limite {plage.duree_max_minutes} min "
                        f"dans la plage {plage.heure_debut}-{plage.heure_fin}"
                    )

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Composer les heures depuis les champs virtuels si presents
        h_d = self.cleaned_data.get("heure_debut_h")
        m_d = self.cleaned_data.get("minute_debut_m")
        h_f = self.cleaned_data.get("heure_fin_h")
        m_f = self.cleaned_data.get("minute_fin_m")

        if h_d is not None and m_d is not None:
            instance.heure_debut = time(int(h_d), int(m_d))
        if h_f is not None and m_f is not None:
            instance.heure_fin = time(int(h_f), int(m_f))

        if commit:
            instance.save()
        return instance


class ReservationModificationForm(ReservationForm):
    """
    Variante de ReservationForm utilisee pour la modification.
    Ajoute la gestion de l'assistance (bool + duree).
    """
    class Meta(ReservationForm.Meta):
        widgets = {
            "date_debut": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "date_fin": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "demande_exception": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "justification": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "est_formation": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "courriels_formes": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Pre-remplir les champs virtuels avec l'instance en cours
        if self.instance and self.instance.pk:
            if self.instance.heure_debut:
                self.fields["heure_debut_h"].initial = f"{self.instance.heure_debut.hour:02d}"
                self.fields["minute_debut_m"].initial = f"{self.instance.heure_debut.minute - self.instance.heure_debut.minute % 10:02d}"
            if self.instance.heure_fin:
                self.fields["heure_fin_h"].initial = f"{self.instance.heure_fin.hour:02d}"
                self.fields["minute_fin_m"].initial = f"{self.instance.heure_fin.minute - self.instance.heure_fin.minute % 10:02d}"

        # Restrictions si pas admin
        is_admin = False
        if self.request and self.request.user.is_authenticated:
            is_admin = self.request.user.is_staff or (hasattr(self.request.user, 'accounts') and self.request.user.usager.est_admin)

        if not is_admin:
            self.fields["assistance"].disabled = True
            self.fields["duree_assistance_minutes"].disabled = True
