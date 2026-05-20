# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NoCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

"""
Module: facturation.forms
--------------------------
Formulaires pour la génération et l’export de factures.

Actuellement :
- FacturationForm : permet à un administrateur de définir une période
  de facturation, avec filtres par affiliations et option d’export CSV.
"""

from django import forms
from accounts.models import Affiliation


class FacturationForm(forms.Form):
    """
    Formulaire de génération de factures.

    Fields:
        - start_date (date) : début de la période.
        - end_date (date)   : fin de la période.
        - affiliations      : filtre optional par affiliation (YourUniversity, McGill…).
        - inclure_csv       : inclure un CSV détaillé par lab.

    Validation :
        - La date de fin doit être ≥ date de début.
    """

    start_date = forms.DateField(
        label="Date de début",
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )

    end_date = forms.DateField(
        label="Date de fin",
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )

    affiliations = forms.ModelMultipleChoiceField(
        label="Limiter aux affiliations suivantes (facultatif)",
        queryset=Affiliation.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 6, "class": "form-control"}),
    )

    inclure_csv = forms.BooleanField(
        label="Inclure un fichier CSV détaillé par laboratory",
        required=False,
        initial=False,
    )

    def clean(self):
        cleaned_data = super().clean()
        d1, d2 = cleaned_data.get("start_date"), cleaned_data.get("end_date")

        if d1 and d2 and d2 < d1:
            raise forms.ValidationError(
                "La date de fin doit être postérieure à la date de début."
            )
        return cleaned_data
