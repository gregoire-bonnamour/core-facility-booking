# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NoCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

"""
Module: facturation.utils
--------------------------
Roles utilitaires pour la génération des données de facturation
(filtrage des réservations, calcul des coûts, exports CSV et PDF).

Modèle métier
-------------
- Rate d'utilisation (horaire) = Rate(equipment, affiliation).hourly_rate
- Rate d'assistance            = Affiliation.assistance_rate (unique par affiliation)
- Formation :
    * tarif fixe par couple (équipement, affiliation)

Roles publiques (API)
-------------------------
- filter_reservations_by_laboratory(start_date, end_date) -> dict[lab:str, list[Reservation]]
- calculer_cout(reservation) -> float
- generate_csv_by_laboratory(groups_by_lab) -> io.BytesIO (ZIP)
- generer_pdfs_par_labo(groups_by_lab, start_date=None, end_date=None) -> dict[nom_pdf:str, bytes]

Dépendances clés
----------------
- reserv.models.Reservation
- equipment_set.models (Rate, TrainingRate)
- user_profile.models (Affiliation, Laboratory via Reservation.user_profile)
- weasyprint (HTML → PDF)
"""

from collections import defaultdict
from django.utils.timezone import now
from booking.models import Reservation
import io, re, csv, zipfile, tempfile, os
from decimal import Decimal
from django.template.loader import render_to_string
try:
    from weasyprint import HTML
except ImportError:
    HTML = None
from datetime import datetime
from django.conf import settings
from accounts.models import UserProfile
from equipment.models import TrainingRate
import logging

logger = logging.getLogger(__name__)
DEBUG_FACTURATION = False


# -------------------------------------------------------------------
#  Rates
# -------------------------------------------------------------------

# -------------------------------------------------------------------
#  Rates
# -------------------------------------------------------------------

def get_hourly_rate(equipment, affiliation):
    from equipment.models import Rate  # import local pour prévenir import circulaire
    if not equipment or not affiliation:
        return Decimal("0.00")
    try:
        t = Rate.objects.get(equipment=equipment, affiliation=affiliation)
        return Decimal(t.hourly_rate)
    except Rate.DoesNotExist:
        return Decimal("0.00")


def get_assistance_rate(affiliation):
    if not affiliation:
        return Decimal("0.00")
    value = getattr(affiliation, "assistance_rate", None)
    return Decimal(value) if value is not None else Decimal("0.00")


#Lecture du tarif fixe de formation
def get_training_fee(equipment, affiliation):
    """
    Returns le tarif fixe de formation pour un couple (équipement, affiliation).
    Si no tarif n’est défini, retourne None.
    """
    try:
        tf = TrainingRate.objects.get(equipment=equipment, affiliation=affiliation)
        return tf.training_fee
    except TrainingRate.DoesNotExist:
        return None


# -------------------------------------------------------------------
#  Filtrage / groupement
# -------------------------------------------------------------------

def filter_reservations_by_laboratory(start_date, end_date):
    reservations = Reservation.objects.filter(
        start_date__gte=start_date,
        end_date__lte=end_date,
        end_date__lt=now()
    ).select_related('user_profile__laboratory', 'user_profile__affiliation', 'equipment')

    groups_by_lab = defaultdict(list)
    for resa in reservations:
        # [NEW LOGIC] Pour les formations, on regarde les PARTICIPANTS
        if resa.is_training:
             participants = get_usagers_facturables(resa)
             for u in participants:
                 lab = u.laboratory.name if u and u.laboratory else "Unknown"
                 # On stocke des tuples (reservation, usager_a_facturer) pour savoir qui facturer
                 # Mais les roles existantes attendent une liste de 'Reservation'.
                 # TASTY TRICK: On ajoute la reservation dans la liste du lab du PARTICIPANT.
                 # Lors du découpage, 'generer_lignes_facturation' saura filtrer que ce lab ne doit payer QUE pour ce participant.
                 groups_by_lab[lab].append(resa)
             
             # Si no participant trouvé, fall-back sur l'organisateur (comportement by default) ?
             if not participants:
                 lab = resa.user_profile.laboratory.name if resa.user_profile and resa.user_profile.laboratory else "Unknown"
                 groups_by_lab[lab].append(resa)
                 
        else:
            # Cas standard : Organisateur
            lab = resa.user_profile.laboratory.name if resa.user_profile and resa.user_profile.laboratory else "Unknown"
            groups_by_lab[lab].append(resa)

    return groups_by_lab


# -------------------------------------------------------------------
#  Décomposition réservation (source de vérité pour calculs)
# -------------------------------------------------------------------

def _heures_reservation(reservation):
    debut = datetime.combine(reservation.start_date, reservation.start_time)
    fin = datetime.combine(reservation.end_date, reservation.end_time)
    return Decimal(max((fin - debut).total_seconds() / 3600, 0))


def decouper_reservation(reservation):
    """
    OBSOLÈTE POUR FACTURATION FORMATION (Legacy support for Stats).
    Transforme une réservation en une ligne de facturation unique.
    
    ATTENTION : Pour les formations, ne retourne que la ligne "organisateur".
    """
    user_profile = reservation.user_profile
    affiliation = user_profile.affiliation if user_profile else None
    equipment = reservation.equipment

    if reservation.is_training:
        tarif_fixe = get_training_fee(equipment, affiliation)
        return {
            "equipment": equipment,
            "user_profile": user_profile,
            "affiliation": affiliation,
            "type": "formation",
            "usage_heures": Decimal("0.0"),
            "usage_taux": Decimal("0.00"),
            "usage_cout": Decimal("0.00"),
            "assistance_heures": Decimal("0.0"),
            "assistance_taux": Decimal("0.00"),
            "assistance_cout": Decimal("0.00"),
            "total": Decimal(tarif_fixe) if tarif_fixe else Decimal("0.00"),
            "note": "Rate fixe de formation appliqué (Organisateur)",
        }

    # --- Cas normal ---
    duree_heures = reservation.duree_heures
    usage_h = Decimal(duree_heures)
    assistance_h = Decimal(0)
    if reservation.assistance:
        assistance_h = Decimal(reservation.assistance_duration_minutes) / 60

    tarif_usage = get_hourly_rate(equipment, affiliation)
    assistance_rate = get_assistance_rate(affiliation)

    cout_usage = usage_h * tarif_usage
    cout_assistance = assistance_h * assistance_rate

    return {
        "equipment": equipment,
        "user_profile": user_profile,
        "affiliation": affiliation,
        "type": "reservation",
        "usage_heures": usage_h,
        "usage_taux": tarif_usage,
        "usage_cout": cout_usage,
        "assistance_heures": assistance_h,
        "assistance_taux": assistance_rate,
        "assistance_cout": cout_assistance,
        "total": cout_usage + cout_assistance,
        "note": "",
    }

def generer_lignes_facturation(reservation):
    """
    Nouveau standard : Returns une LISTE de lignes de facturation.
    Gère le cas 1 réservation -> N participants (formation).
    """
    lignes = []
    
    if reservation.is_training:
        participants = get_usagers_facturables(reservation)
        
        if not participants:
            # Fallback : Si no participant, on ne facture PERSONNE (demande utilisateur).
            # On génère quand même une ligne pour la traçabilité (Organizer, 0$), avec une note explicite.
            user_profile = reservation.user_profile
            affiliation = user_profile.affiliation if user_profile else None
            lignes.append({
                "equipment": reservation.equipment,
                "user_profile": user_profile,
                "affiliation": affiliation,
                "type": "formation",
                "usage_heures": Decimal("0.0"),
                "usage_taux": Decimal("0.00"),
                "usage_cout": Decimal("0.00"),
                "assistance_heures": Decimal("0.0"),
                "assistance_taux": Decimal("0.00"),
                "assistance_cout": Decimal("0.00"),
                "total": Decimal("0.00"),
                "note": "Formation sans participants (No facturée)",
            })
        else:
            for u in participants:
                affiliation = u.affiliation if u else None
                tarif_fixe = get_training_fee(reservation.equipment, affiliation)
                
                lignes.append({
                    "equipment": reservation.equipment,
                    "user_profile": u, # LE PARTICIPANT
                    "affiliation": affiliation,
                    "type": "formation",
                    "usage_heures": Decimal("0.0"),
                    "usage_taux": Decimal("0.00"),
                    "usage_cout": Decimal("0.00"),
                    "assistance_heures": Decimal("0.0"),
                    "assistance_taux": Decimal("0.00"),
                    "assistance_cout": Decimal("0.00"),
                    "total": Decimal(tarif_fixe) if tarif_fixe else Decimal("0.00"),
                    "note": f"Formation (Participant: {u.first_name} {u.name})",
                })
    else:
        # Cas classique : 1 ligne
        lignes.append(decouper_reservation(reservation))
        
    return lignes

# -------------------------------------------------------------------
#  Calcul simple (API conservée)
# -------------------------------------------------------------------

def calculer_cout(reservation):
    """
    Returns le coût TOTAL de la réservation (somme de tous les participants).
    """
    lignes = generer_lignes_facturation(reservation)
    return float(sum(l["total"] for l in lignes))


# -------------------------------------------------------------------
#  Exports (CSV / PDF)
# -------------------------------------------------------------------

def generate_csv_by_laboratory(groups_by_lab):
    """
    Génère un ZIP contenant un CSV par laboratory.
    """
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for lab_name, reservations in groups_by_lab.items():
            csv_buffer = io.StringIO(newline='')  
            writer = csv.writer(csv_buffer)
            csv_buffer.write('\ufeff')

            writer.writerow([
                "Laboratory", "UserProfile", "Affiliation", "Équipement", "Type",
                "Date début", "Date fin",
                "Durée usage (h)", "Coût usage ($)",
                "Durée assistance (h)", "Coût assistance ($)",
                "Total ($)",
            ])
            
            # Pour éviter les doublons si 'reservation' apparait 2 fois dans la liste (ex: 2 participants du même lab)
            # On doit itérer sur les RÉSERVATIONS, mais générer les LIGNES pertinentes pour CE lab.
            
            # Problème : 'reservations' contient la réservation brute.
            # generer_lignes_facturation(r) retourne TOUS les participants (Lab A, Lab B...).
            # On ne veut garder que les lignes qui concernent 'lab_name'.
            

            
            # Set unique de réservations pour ce lab
            unique_resas = set(reservations)
            
            for resa in unique_resas:
                all_lines = generer_lignes_facturation(resa)
                for d in all_lines:
                    # Filtre Labo effectif
                    u_labo = "Unknown"
                    if d['user_profile'] and d['user_profile'].laboratory:
                        u_labo = d['user_profile'].laboratory.name
                    
                    if u_labo == lab_name:
                         user_profile = d['user_profile']
                         type_lib = "Formation" if d['type'] == 'formation' else "Réservation"
                         
                         writer.writerow([
                            lab_name,
                            f"{user_profile.first_name} {user_profile.name}" if user_profile else "Unknown",
                            user_profile.affiliation.name if user_profile and user_profile.affiliation else "Unknowne",
                            d['equipment'].name,
                            type_lib,
                            resa.start_date.strftime("%Y-%m-%d"),
                            resa.end_date.strftime("%Y-%m-%d"),
                            f"{d['usage_heures']:.2f}",
                            f"{d['usage_cout']:.2f}",
                            f"{d['assistance_heures']:.2f}",
                            f"{d['assistance_cout']:.2f}",
                            f"{d['total']:.2f}",
                        ])
            
            safe_labo = re.sub(r'[^A-Za-z0-9_\-]+', '_', lab_name)
            zip_file.writestr(f"Facture_Laboratory_{safe_labo}.csv", csv_buffer.getvalue())

    zip_buffer.seek(0)
    return zip_buffer


def generer_pdfs_par_labo(groups_by_lab, start_date=None, end_date=None):
    """
    Génère des PDFs (un par laboratory) récapitulant l'activité et les coûts.
    """
    pdfs = {}
    if HTML is None:
        raise RuntimeError("WeasyPrint n'est pas installé.")
    from decimal import Decimal

    for lab, reservations in groups_by_lab.items():
        total_labo = Decimal("0.00")
        usagers_context = []

        # --- Étape 1 : regroupement ---
        regroupement = defaultdict(lambda: defaultdict(lambda: defaultdict(Decimal)))

        # Set unique pour éviter doublons (même logique que CSV)
        unique_resas = set(reservations)

        for resa in unique_resas:
            all_lines = generer_lignes_facturation(resa)
            
            for d in all_lines:
                # Filtre : cette ligne appartient-elle à ce lab ?
                u_labo = "Unknown"
                if d['user_profile'] and d['user_profile'].laboratory:
                    u_labo = d['user_profile'].laboratory.name
                
                if u_labo != lab:
                    continue

                user_profile = d['user_profile']
                equipement_nom = d['equipment'].name

                if d['type'] == 'formation':
                    regroupement[user_profile][equipement_nom]["Formation_duree"] += Decimal(0)
                    regroupement[user_profile][equipement_nom]["Formation_tarif"] = d["total"] # Dernier tarif vu (supposons unique)
                    regroupement[user_profile][equipement_nom]["Formation_cout"] += d["total"]
                    total_labo += d["total"]
                else:
                    # Utilisation
                    if d["usage_heures"] > 0:
                        regroupement[user_profile][equipement_nom]["Utilisation_duree"] += d["usage_heures"]
                        regroupement[user_profile][equipement_nom]["Utilisation_tarif"] = d["usage_taux"]
                        regroupement[user_profile][equipement_nom]["Utilisation_cout"] += d["usage_cout"]
                        total_labo += d["usage_cout"]

                    # Assistance
                    if d["assistance_heures"] > 0:
                        regroupement[user_profile][equipement_nom]["Assistance_duree"] += d["assistance_heures"]
                        regroupement[user_profile][equipement_nom]["Assistance_tarif"] = d["assistance_taux"]
                        regroupement[user_profile][equipement_nom]["Assistance_cout"] += d["assistance_cout"]
                        total_labo += d["assistance_cout"]

        # --- Étape 2 : transformer regroupement en structure pour template ---
        for user_profile, equipment_set in regroupement.items():
            equipements_context = []
            total_usager = Decimal("0.00")

            for eq_nom, lignes in equipment_set.items():
                lignes_context = []

                # Utilisation
                if "Utilisation_cout" in lignes:
                    lignes_context.append({
                        "type": "Utilisation",
                        "duree": round(lignes["Utilisation_duree"], 2),
                        "tarif": round(lignes["Utilisation_tarif"], 2),
                        "cout": round(lignes["Utilisation_cout"], 2),
                    })
                    total_usager += lignes["Utilisation_cout"]

                # Assistance
                if "Assistance_cout" in lignes:
                    lignes_context.append({
                        "type": "Assistance",
                        "duree": round(lignes["Assistance_duree"], 2),
                        "tarif": round(lignes["Assistance_tarif"], 2),
                        "cout": round(lignes["Assistance_cout"], 2),
                    })
                    total_usager += lignes["Assistance_cout"]

                # Formation
                if "Formation_cout" in lignes:
                    lignes_context.append({
                        "type": "Formation",
                        "duree": None,
                        "tarif": round(lignes["Formation_tarif"], 2),
                        "cout": round(lignes["Formation_cout"], 2),
                    })
                    total_usager += lignes["Formation_cout"]

                equipements_context.append({
                    "name": eq_nom,
                    "lignes": lignes_context,
                    "total_equipement": round(sum(l["cout"] for l in lignes_context), 2),
                })

            usagers_context.append({
                "user_profile": user_profile,
                "equipment": equipements_context,
                "total_usager": round(total_usager, 2),
            })

        # --- Étape 3 : préparer contexte ---
        context = {
            "laboratory": {"name": lab},
            "start_date": start_date,
            "end_date": end_date,
            "user_profiles": usagers_context,
            "total_laboratoire": round(total_labo, 2),
            "logo_path": f"file://{settings.BASE_DIR}/billing/static/billing/images/YourUniversity.png",
        }

        rendered_html = render_to_string("billing/facture_labo.html", context)

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmpfile:
            tmpfile_path = tmpfile.name

        HTML(string=rendered_html).write_pdf(tmpfile_path)

        with open(tmpfile_path, 'rb') as f:
            pdf_content = f.read()

        os.remove(tmpfile_path)

        nom_fichier = f"Facture_Laboratory_{lab.replace(' ', '_')}.pdf"
        pdfs[nom_fichier] = pdf_content

    return pdfs



def get_usagers_facturables(reservation):
    """
    Returns les user_profiles qui doivent être facturés pour une réservation.

    - Cas normal → l’user_profile lié à la réservation.
    - Cas formation → uniquement les user_profiles listés dans trained_emails
      (s’ils existent dans la base UserProfile).
    """
    # Cas normal (réservation classique)
    if not reservation.is_training and reservation.user_profile:
        return [reservation.user_profile]

    # Cas formation
    user_profiles = []
    if reservation.is_training and reservation.trained_emails:
        # [MODIF] Parsing robuste (virgule, point-virgule, newline)
        raw = reservation.trained_emails
        emails = [c.strip() for c in re.split(r'[;,\n\r]+', raw) if c.strip()]
        
        for email in emails:
            u = UserProfile.objects.filter(email__iexact=email).first()
            if u and u not in user_profiles:
                user_profiles.append(u)
        logger.info(f"[FACTURATION] Formation {reservation.id} – {len(user_profiles)} user_profiles facturables trouvés")

    return user_profiles

