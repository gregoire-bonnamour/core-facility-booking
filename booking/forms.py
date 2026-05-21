# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NoCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

"""
Module: reserv.forms
---------------------
Formulaires lies aux reservations.

Deux formulaires principaux :
- ReservationForm             : creation de reservation avec toutes les regles metier.
- ReservationModificationForm : modification, incluant l'assistance.

Regles implementees :
- Regles de base (dates futures, coherence debut/fin, pas de chevauchement).
- Gestion des demandes exceptionnelles (bypass des regles optionalles).
- Validation par rapport aux creneaux autorises.
- Validation par rapport aux plages limites (duree max par user_profile).
"""

from django import forms
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import Reservation
from equipment.models import TimeSlot, UsageQuota
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
    start_time_h = forms.ChoiceField(choices=HOUR_CHOICES, label="Start hour")
    start_minute_m = forms.ChoiceField(choices=MINUTE_CHOICES, label="Start minute")
    end_time_h = forms.ChoiceField(choices=HOUR_CHOICES, label="End hour")
    end_minute_m = forms.ChoiceField(choices=MINUTE_CHOICES, label="End minute")

    # Champs virtuels (ne se sauvegardent PAS dans la DB)
    # Ils servent uniquement a l'interface pour les admins
    is_maintenance = forms.BooleanField(
        required=False,
        label="Maintenance Reservation",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        help_text="Reservation will be assigned to the system 'Maintenance' user profile"
    )
    is_teaching = forms.BooleanField(
        required=False,
        label="Teaching Reservation",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        help_text="Reservation will be assigned to the system 'Teaching' user profile"
    )

    start_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}, format="%Y-%m-%d"),
        input_formats=["%Y-%m-%d"],
        required=True,
        label="Debut :",
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}, format="%Y-%m-%d"),
        input_formats=["%Y-%m-%d"],
        required=True,
        label="Fin :",
    )

    class Meta:
        model = Reservation
        fields = [
            "start_date",
            "end_date",
            "start_time_h", "start_minute_m",
            "end_time_h", "end_minute_m",
            "exception_request",
            "justification",
            "is_training",
            "trained_emails",
            "assistance",
            "assistance_duration_minutes",
        ]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "end_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "exception_request": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "justification": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "is_training": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "trained_emails": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }
        help_texts = {
            "is_training": "Check if this reservation is a training session (billed at flat rate).",
            "trained_emails": "Saisissez les emails des participants (separes par des virgules, points-virgules ou sauts de ligne).",
        }

    def __init__(self, *args, **kwargs):
        self.user_profile = kwargs.pop('user_profile', None)
        self.equipment = kwargs.pop('equipment', None)
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        # Champs non obligatoires
        self.fields['justification'].required = False
        self.fields['trained_emails'].required = False
        self.fields['assistance_duration_minutes'].required = False
        self.fields['assistance_duration_minutes'].widget = forms.NumberInput(attrs={'min': 0, 'step': 5})

        # Masquer certains champs pour les non-admin
        is_admin = False
        if self.request and self.request.user.is_authenticated:
            is_admin = self.request.user.is_staff or (hasattr(self.request.user, 'user_profile') and self.request.user.user_profile.is_platform_admin)

        if not is_admin:
            self.fields['is_training'].widget = forms.HiddenInput()
            self.fields['is_training'].initial = False
            self.fields['trained_emails'].widget = forms.HiddenInput()
            self.fields['is_maintenance'].widget = forms.HiddenInput()
            self.fields['is_teaching'].widget = forms.HiddenInput()

    def clean(self):
        cleaned_data = super().clean()

        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        exception_request = cleaned_data.get("exception_request")
        justification = cleaned_data.get("justification")

        # Recomposition des heures
        h_d = cleaned_data.get("start_time_h")
        m_d = cleaned_data.get("start_minute_m")
        h_f = cleaned_data.get("end_time_h")
        m_f = cleaned_data.get("end_minute_m")

        start_time = time(int(h_d), int(m_d)) if h_d and m_d else None
        end_time = time(int(h_f), int(m_f)) if h_f and m_f else None

        # Injecter dans cleaned_data -> correspondance avec le modele
        cleaned_data["start_time"] = start_time
        cleaned_data["end_time"] = end_time

        if not start_date or not end_date or not start_time or not end_time:
            return cleaned_data  # stop si donnees incompletes

        dt_debut = timezone.make_aware(datetime.combine(start_date, start_time))
        dt_fin = timezone.make_aware(datetime.combine(end_date, end_time))

        # 1. Reservation future
        if dt_debut < timezone.now():
            self.add_error("start_date", "The reservation must start in the future.")

        # 2. Debut < fin
        if dt_debut >= dt_fin:
            self.add_error("start_time_h", "The start time must be before the end time.")
            self.add_error("end_time_h", "The end time must be after the start time.")

        # 3. Chevauchement
        if self.equipment:
            conflits = (
                Reservation.objects
                .filter(equipment=self.equipment)
                .exclude(pk=self.instance.pk)
                .exclude(status__in=['cancelled', 'past'])
            )
            for r in conflits:
                r_debut = timezone.make_aware(datetime.combine(r.start_date, r.start_time))
                r_fin = timezone.make_aware(datetime.combine(r.end_date, r.end_time))
                if dt_debut < r_fin and dt_fin > r_debut:
                    raise ValidationError(
                        f"Overlaps with another reservation: {r.start_date} {r.start_time}-{r.end_time}"
                    )

        # 4. Duree maximale globale (parametre equipment)
        duree_totale = dt_fin - dt_debut
        if self.equipment and not exception_request:
            duree_max = getattr(self.equipment, "max_duration_hours", 72)
            if duree_totale > timedelta(hours=duree_max):
                raise ValidationError(
                    f"The reservation exceeds the maximum allowed duration of {duree_max}h "
                    f"pour cet equipment (sauf demande exceptionnelle)."
                )

        # 5. Exception -> justification obligatoire
        if exception_request and not justification:
            self.add_error("justification", "Please explain the exception request.")

        # Validation Assistance : Duree obligatoire si coche
        assistance = cleaned_data.get("assistance")
        duree_assistance = cleaned_data.get("assistance_duration_minutes")
        if assistance and (duree_assistance is None or duree_assistance <= 0):
            self.add_error("assistance_duration_minutes", "Assistance duration is required when assistance is requested.")

        # Validation : Maintenance et Enseignement sont mutuellement exclusifs
        type_maint = cleaned_data.get("is_maintenance", False)
        type_enseign = cleaned_data.get("is_teaching", False)
        if type_maint and type_enseign:
            raise ValidationError(
                "A reservation cannot be both Maintenance and Teaching at the same time. "
                "Veuillez ne cocher qu'une seule option."
            )

        if exception_request:
            return cleaned_data  # on bypass les regles optionalles (creneaux, plages)

        # 6. Respect des creneaux autorises
        time_slots = TimeSlot.objects.filter(equipment=self.equipment, day_of_week=start_date.weekday())
        if time_slots.exists():
            touche, respecte = False, False
            for c in time_slots:
                if (start_time < c.end_time and end_time > c.start_time):
                    touche = True
                    if c.start_time <= start_time and c.end_time >= end_time:
                        respecte = True
                        break
            if touche and not respecte:
                raise ValidationError("Reservation is outside the authorized time slots for this day.")

        # 7. Limites cumulees
        quotas = UsageQuota.objects.filter(equipment=self.equipment, day_of_week=start_date.weekday())
        for quota in quotas:
            if quota.start_time <= start_time < quota.end_time or quota.start_time < end_time <= quota.end_time:
                total = timedelta()
                reservations = Reservation.objects.filter(
                    user_profile=self.user_profile,
                    equipment=self.equipment,
                    start_date=start_date,
                    status__in=['upcoming', 'pending'],
                    start_time__lt=quota.end_time,
                    end_time__gt=quota.start_time,
                )
                if self.instance.pk:
                    reservations = reservations.exclude(pk=self.instance.pk)

                for r in reservations:
                    total += datetime.combine(start_date, r.end_time) - datetime.combine(start_date, r.start_time)

                total += dt_fin - dt_debut
                if total > timedelta(minutes=quota.max_duration_minutes):
                    raise ValidationError(
                        f"Total duration ({total}) exceeds the {quota.max_duration_minutes} min limit "
                        f"for the window {quota.start_time}-{quota.end_time}"
                    )

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Composer les heures depuis les champs virtuels si presents
        h_d = self.cleaned_data.get("start_time_h")
        m_d = self.cleaned_data.get("start_minute_m")
        h_f = self.cleaned_data.get("end_time_h")
        m_f = self.cleaned_data.get("end_minute_m")

        if h_d is not None and m_d is not None:
            instance.start_time = time(int(h_d), int(m_d))
        if h_f is not None and m_f is not None:
            instance.end_time = time(int(h_f), int(m_f))

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
            "start_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "end_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "exception_request": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "justification": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "is_training": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "trained_emails": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Pre-remplir les champs virtuels avec l'instance en cours
        if self.instance and self.instance.pk:
            if self.instance.start_time:
                self.fields["start_time_h"].initial = f"{self.instance.start_time.hour:02d}"
                self.fields["start_minute_m"].initial = f"{self.instance.start_time.minute - self.instance.start_time.minute % 10:02d}"
            if self.instance.end_time:
                self.fields["end_time_h"].initial = f"{self.instance.end_time.hour:02d}"
                self.fields["end_minute_m"].initial = f"{self.instance.end_time.minute - self.instance.end_time.minute % 10:02d}"

        # Restrictions si pas admin
        is_admin = False
        if self.request and self.request.user.is_authenticated:
            is_admin = self.request.user.is_staff or (hasattr(self.request.user, 'user_profile') and self.request.user.user_profile.is_platform_admin)

        if not is_admin:
            self.fields["assistance"].disabled = True
            self.fields["assistance_duration_minutes"].disabled = True
