from accounts.utils import est_admin_plateforme
# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

"""
Module : facturation.views
--------------------------
Vues de l’application `facturation`.

- generer_factures : génération de factures par laboratoire
  (PDF obligatoires, CSV optionnel) pour une période donnée.
"""
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render
from django.http import HttpResponse
from .forms import FacturationForm
from .utils import (
    filtrer_reservations_par_laboratoire,
    generer_csv_par_laboratoire,
    generer_pdfs_par_labo,
)
import zipfile
import io
import logging

logger = logging.getLogger(__name__)


def est_admin_plateforme(user):
    return user.is_staff or user.is_superuser or (hasattr(user, 'accounts') and user.usager.est_admin)

@user_passes_test(est_admin_plateforme)
def generer_factures(request):
    """
    Génère les factures (PDF/CSV) regroupées par laboratoire
    sur la période sélectionnée.
    """
    if request.method == 'POST':
        form = FacturationForm(request.POST)
        if form.is_valid():
            date_debut = form.cleaned_data['date_debut']
            date_fin = form.cleaned_data['date_fin']
            affiliations = form.cleaned_data['affiliations']
            inclure_csv = form.cleaned_data['inclure_csv']

            # --- Étape 1 : Filtrage initial ---
            groupes = filtrer_reservations_par_laboratoire(date_debut, date_fin)
            logger.debug(f"Réservations brutes par labo : "
                         f"{[(l, len(r)) for l, r in groupes.items()]}")

            # --- Étape 2 : Filtre par affiliation (optionnel) ---
            # --- Étape 2 : Filtre par affiliation (optionnel) ---
            if affiliations.exists():
                # [MODIF] Pour les formations, on doit vérifier l'affiliation du PARTICIPANT du labo
                # et non celle de l'organisateur (qui peut être différent).
                from .utils import get_usagers_facturables
                
                def _check_affiliation(resa, labo_nom, affiliations_demandees):
                    # 1. Qui paye pour cette réservation ?
                    payeurs = get_usagers_facturables(resa)
                    
                    # 2. On cherche le payeur qui appartient à 'labo_nom'
                    # (car 'resa' est dans le bucket 'labo_nom')
                    for u in payeurs:
                        if u and u.laboratoire and u.laboratoire.nom == labo_nom:
                            return u.affiliation in affiliations_demandees
                            
                    # Fallback (si pas trouvé, ex: labo changé entre temps ? ou cas standard)
                    if resa.usager and resa.usager.affiliation:
                        return resa.usager.affiliation in affiliations_demandees
                    return False

                new_groupes = {}
                for labo, resas in groupes.items():
                    resas_filtrees = [
                        r for r in resas 
                        if _check_affiliation(r, labo, affiliations)
                    ]
                    if resas_filtrees:
                        new_groupes[labo] = resas_filtrees
                groupes = new_groupes

                logger.debug(f"Après filtre affiliations : "
                             f"{[(l, len(r)) for l, r in groupes.items()]}")

            # --- Étape 3 : Nettoyage ---
            groupes = {l: r for l, r in groupes.items() if r}
            logger.debug(f"Labos retenus : "
                         f"{[(l, len(r)) for l, r in groupes.items()]}")

            # --- Étape 4 : Génération des PDF ---
            pdfs = generer_pdfs_par_labo(groupes, date_debut, date_fin)

            # --- Étape 5 : Construction du ZIP ---
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                # PDFs
                for nom_fichier, contenu in pdfs.items():
                    zip_file.writestr(nom_fichier, contenu)

                # CSVs optionnels
                if inclure_csv:
                    csv_archive = generer_csv_par_laboratoire(groupes)
                    with zipfile.ZipFile(csv_archive) as csv_zip:
                        for name in csv_zip.namelist():
                            zip_file.writestr(name, csv_zip.read(name))

            # --- Étape 6 : Réponse HTTP ---
            zip_buffer.seek(0)
            filename = f"factures_labos_{date_debut}_{date_fin}.zip"
            response = HttpResponse(zip_buffer, content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response

    else:
        form = FacturationForm()

    return render(request, 'facturation/facturation.html', {'form': form})
