# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

"""
Module : facturation.utils
--------------------------
Fonctions utilitaires pour la génération des données de facturation
(filtrage des réservations, calcul des coûts, exports CSV et PDF).

Modèle métier
-------------
- Tarif d'utilisation (horaire) = Tarif(equipement, affiliation).tarif_horaire
- Tarif d'assistance            = Affiliation.tarif_assistance (unique par affiliation)
- Formation :
    * tarif fixe par couple (équipement, affiliation)

Fonctions publiques (API)
-------------------------
- filtrer_reservations_par_laboratoire(date_debut, date_fin) -> dict[labo:str, list[Reservation]]
- calculer_cout(reservation) -> float
- generer_csv_par_laboratoire(groupes_par_labo) -> io.BytesIO (ZIP)
- generer_pdfs_par_labo(groupes_par_labo, date_debut=None, date_fin=None) -> dict[nom_pdf:str, bytes]

Dépendances clés
----------------
- reserv.models.Reservation
- equipements.models (Tarif, TarifFormation)
- usager.models (Affiliation, Laboratoire via Reservation.usager)
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
from accounts.models import Usager
from equipment.models import TarifFormation
import logging

logger = logging.getLogger(__name__)
DEBUG_FACTURATION = False


# -------------------------------------------------------------------
#  Tarifs
# -------------------------------------------------------------------

# -------------------------------------------------------------------
#  Tarifs
# -------------------------------------------------------------------

def get_tarif_horaire(equipement, affiliation):
    from equipment.models import Tarif  # import local pour prévenir import circulaire
    if not equipement or not affiliation:
        return Decimal("0.00")
    try:
        t = Tarif.objects.get(equipement=equipement, affiliation=affiliation)
        return Decimal(t.tarif_horaire)
    except Tarif.DoesNotExist:
        return Decimal("0.00")


def get_tarif_assistance(affiliation):
    if not affiliation:
        return Decimal("0.00")
    value = getattr(affiliation, "tarif_assistance", None)
    return Decimal(value) if value is not None else Decimal("0.00")


#Lecture du tarif fixe de formation
def get_tarif_formation(equipement, affiliation):
    """
    Retourne le tarif fixe de formation pour un couple (équipement, affiliation).
    Si aucun tarif n’est défini, retourne None.
    """
    try:
        tf = TarifFormation.objects.get(equipement=equipement, affiliation=affiliation)
        return tf.tarif_formation
    except TarifFormation.DoesNotExist:
        return None


# -------------------------------------------------------------------
#  Filtrage / groupement
# -------------------------------------------------------------------

def filtrer_reservations_par_laboratoire(date_debut, date_fin):
    reservations = Reservation.objects.filter(
        date_debut__gte=date_debut,
        date_fin__lte=date_fin,
        date_fin__lt=now()
    ).select_related('usager__laboratoire', 'usager__affiliation', 'equipement')

    groupes_par_labo = defaultdict(list)
    for resa in reservations:
        # [NEW LOGIC] Pour les formations, on regarde les PARTICIPANTS
        if resa.est_formation:
             participants = get_usagers_facturables(resa)
             for u in participants:
                 labo = u.laboratoire.nom if u and u.laboratoire else "Inconnu"
                 # On stocke des tuples (reservation, usager_a_facturer) pour savoir qui facturer
                 # Mais les fonctions existantes attendent une liste de 'Reservation'.
                 # TASTY TRICK: On ajoute la reservation dans la liste du labo du PARTICIPANT.
                 # Lors du découpage, 'generer_lignes_facturation' saura filtrer que ce labo ne doit payer QUE pour ce participant.
                 groupes_par_labo[labo].append(resa)
             
             # Si aucun participant trouvé, fall-back sur l'organisateur (comportement par défaut) ?
             if not participants:
                 labo = resa.usager.laboratoire.nom if resa.usager and resa.usager.laboratoire else "Inconnu"
                 groupes_par_labo[labo].append(resa)
                 
        else:
            # Cas standard : Organisateur
            labo = resa.usager.laboratoire.nom if resa.usager and resa.usager.laboratoire else "Inconnu"
            groupes_par_labo[labo].append(resa)

    return groupes_par_labo


# -------------------------------------------------------------------
#  Décomposition réservation (source de vérité pour calculs)
# -------------------------------------------------------------------

def _heures_reservation(reservation):
    debut = datetime.combine(reservation.date_debut, reservation.heure_debut)
    fin = datetime.combine(reservation.date_fin, reservation.heure_fin)
    return Decimal(max((fin - debut).total_seconds() / 3600, 0))


def decouper_reservation(reservation):
    """
    OBSOLÈTE POUR FACTURATION FORMATION (Legacy support for Stats).
    Transforme une réservation en une ligne de facturation unique.
    
    ATTENTION : Pour les formations, ne retourne que la ligne "organisateur".
    """
    usager = reservation.usager
    affiliation = usager.affiliation if usager else None
    equipement = reservation.equipement

    if reservation.est_formation:
        tarif_fixe = get_tarif_formation(equipement, affiliation)
        return {
            "equipement": equipement,
            "accounts": usager,
            "affiliation": affiliation,
            "type": "formation",
            "usage_heures": Decimal("0.0"),
            "usage_taux": Decimal("0.00"),
            "usage_cout": Decimal("0.00"),
            "assistance_heures": Decimal("0.0"),
            "assistance_taux": Decimal("0.00"),
            "assistance_cout": Decimal("0.00"),
            "total": Decimal(tarif_fixe) if tarif_fixe else Decimal("0.00"),
            "note": "Tarif fixe de formation appliqué (Organisateur)",
        }

    # --- Cas normal ---
    duree_heures = reservation.duree_heures
    usage_h = Decimal(duree_heures)
    assistance_h = Decimal(0)
    if reservation.assistance:
        assistance_h = Decimal(reservation.duree_assistance_minutes) / 60

    tarif_usage = get_tarif_horaire(equipement, affiliation)
    tarif_assistance = get_tarif_assistance(affiliation)

    cout_usage = usage_h * tarif_usage
    cout_assistance = assistance_h * tarif_assistance

    return {
        "equipement": equipement,
        "accounts": usager,
        "affiliation": affiliation,
        "type": "reservation",
        "usage_heures": usage_h,
        "usage_taux": tarif_usage,
        "usage_cout": cout_usage,
        "assistance_heures": assistance_h,
        "assistance_taux": tarif_assistance,
        "assistance_cout": cout_assistance,
        "total": cout_usage + cout_assistance,
        "note": "",
    }

def generer_lignes_facturation(reservation):
    """
    Nouveau standard : Retourne une LISTE de lignes de facturation.
    Gère le cas 1 réservation -> N participants (formation).
    """
    lignes = []
    
    if reservation.est_formation:
        participants = get_usagers_facturables(reservation)
        
        if not participants:
            # Fallback : Si aucun participant, on ne facture PERSONNE (demande utilisateur).
            # On génère quand même une ligne pour la traçabilité (Organizer, 0$), avec une note explicite.
            usager = reservation.usager
            affiliation = usager.affiliation if usager else None
            lignes.append({
                "equipement": reservation.equipement,
                "accounts": usager,
                "affiliation": affiliation,
                "type": "formation",
                "usage_heures": Decimal("0.0"),
                "usage_taux": Decimal("0.00"),
                "usage_cout": Decimal("0.00"),
                "assistance_heures": Decimal("0.0"),
                "assistance_taux": Decimal("0.00"),
                "assistance_cout": Decimal("0.00"),
                "total": Decimal("0.00"),
                "note": "Formation sans participants (Non facturée)",
            })
        else:
            for u in participants:
                affiliation = u.affiliation if u else None
                tarif_fixe = get_tarif_formation(reservation.equipement, affiliation)
                
                lignes.append({
                    "equipement": reservation.equipement,
                    "accounts": u, # LE PARTICIPANT
                    "affiliation": affiliation,
                    "type": "formation",
                    "usage_heures": Decimal("0.0"),
                    "usage_taux": Decimal("0.00"),
                    "usage_cout": Decimal("0.00"),
                    "assistance_heures": Decimal("0.0"),
                    "assistance_taux": Decimal("0.00"),
                    "assistance_cout": Decimal("0.00"),
                    "total": Decimal(tarif_fixe) if tarif_fixe else Decimal("0.00"),
                    "note": f"Formation (Participant: {u.prenom} {u.nom})",
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
    Retourne le coût TOTAL de la réservation (somme de tous les participants).
    """
    lignes = generer_lignes_facturation(reservation)
    return float(sum(l["total"] for l in lignes))


# -------------------------------------------------------------------
#  Exports (CSV / PDF)
# -------------------------------------------------------------------

def generer_csv_par_laboratoire(groupes_par_labo):
    """
    Génère un ZIP contenant un CSV par laboratoire.
    """
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for labo_nom, reservations in groupes_par_labo.items():
            csv_buffer = io.StringIO(newline='')  
            writer = csv.writer(csv_buffer)
            csv_buffer.write('\ufeff')

            writer.writerow([
                "Laboratoire", "Usager", "Affiliation", "Équipement", "Type",
                "Date début", "Date fin",
                "Durée usage (h)", "Coût usage ($)",
                "Durée assistance (h)", "Coût assistance ($)",
                "Total ($)",
            ])
            
            # Pour éviter les doublons si 'reservation' apparait 2 fois dans la liste (ex: 2 participants du même labo)
            # On doit itérer sur les RÉSERVATIONS, mais générer les LIGNES pertinentes pour CE labo.
            
            # Problème : 'reservations' contient la réservation brute.
            # generer_lignes_facturation(r) retourne TOUS les participants (Lab A, Lab B...).
            # On ne veut garder que les lignes qui concernent 'labo_nom'.
            

            
            # Set unique de réservations pour ce labo
            unique_resas = set(reservations)
            
            for resa in unique_resas:
                all_lines = generer_lignes_facturation(resa)
                for d in all_lines:
                    # Filtre Labo effectif
                    u_labo = "Inconnu"
                    if d['accounts'] and d['accounts'].laboratoire:
                        u_labo = d['accounts'].laboratoire.nom
                    
                    if u_labo == labo_nom:
                         usager = d['accounts']
                         type_lib = "Formation" if d['type'] == 'formation' else "Réservation"
                         
                         writer.writerow([
                            labo_nom,
                            f"{usager.prenom} {usager.nom}" if usager else "Inconnu",
                            usager.affiliation.nom if usager and usager.affiliation else "Inconnue",
                            d['equipement'].nom,
                            type_lib,
                            resa.date_debut.strftime("%Y-%m-%d"),
                            resa.date_fin.strftime("%Y-%m-%d"),
                            f"{d['usage_heures']:.2f}",
                            f"{d['usage_cout']:.2f}",
                            f"{d['assistance_heures']:.2f}",
                            f"{d['assistance_cout']:.2f}",
                            f"{d['total']:.2f}",
                        ])
            
            safe_labo = re.sub(r'[^A-Za-z0-9_\-]+', '_', labo_nom)
            zip_file.writestr(f"Facture_Laboratoire_{safe_labo}.csv", csv_buffer.getvalue())

    zip_buffer.seek(0)
    return zip_buffer


def generer_pdfs_par_labo(groupes_par_labo, date_debut=None, date_fin=None):
    """
    Génère des PDFs (un par laboratoire) récapitulant l'activité et les coûts.
    """
    pdfs = {}
    if HTML is None:
        raise RuntimeError("WeasyPrint n'est pas installé.")
    from decimal import Decimal

    for labo, reservations in groupes_par_labo.items():
        total_labo = Decimal("0.00")
        usagers_context = []

        # --- Étape 1 : regroupement ---
        regroupement = defaultdict(lambda: defaultdict(lambda: defaultdict(Decimal)))

        # Set unique pour éviter doublons (même logique que CSV)
        unique_resas = set(reservations)

        for resa in unique_resas:
            all_lines = generer_lignes_facturation(resa)
            
            for d in all_lines:
                # Filtre : cette ligne appartient-elle à ce labo ?
                u_labo = "Inconnu"
                if d['accounts'] and d['accounts'].laboratoire:
                    u_labo = d['accounts'].laboratoire.nom
                
                if u_labo != labo:
                    continue

                usager = d['accounts']
                equipement_nom = d['equipement'].nom

                if d['type'] == 'formation':
                    regroupement[usager][equipement_nom]["Formation_duree"] += Decimal(0)
                    regroupement[usager][equipement_nom]["Formation_tarif"] = d["total"] # Dernier tarif vu (supposons unique)
                    regroupement[usager][equipement_nom]["Formation_cout"] += d["total"]
                    total_labo += d["total"]
                else:
                    # Utilisation
                    if d["usage_heures"] > 0:
                        regroupement[usager][equipement_nom]["Utilisation_duree"] += d["usage_heures"]
                        regroupement[usager][equipement_nom]["Utilisation_tarif"] = d["usage_taux"]
                        regroupement[usager][equipement_nom]["Utilisation_cout"] += d["usage_cout"]
                        total_labo += d["usage_cout"]

                    # Assistance
                    if d["assistance_heures"] > 0:
                        regroupement[usager][equipement_nom]["Assistance_duree"] += d["assistance_heures"]
                        regroupement[usager][equipement_nom]["Assistance_tarif"] = d["assistance_taux"]
                        regroupement[usager][equipement_nom]["Assistance_cout"] += d["assistance_cout"]
                        total_labo += d["assistance_cout"]

        # --- Étape 2 : transformer regroupement en structure pour template ---
        for usager, equipements in regroupement.items():
            equipements_context = []
            total_usager = Decimal("0.00")

            for eq_nom, lignes in equipements.items():
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
                    "nom": eq_nom,
                    "lignes": lignes_context,
                    "total_equipement": round(sum(l["cout"] for l in lignes_context), 2),
                })

            usagers_context.append({
                "accounts": usager,
                "equipment": equipements_context,
                "total_usager": round(total_usager, 2),
            })

        # --- Étape 3 : préparer contexte ---
        context = {
            "laboratoire": {"nom": labo},
            "date_debut": date_debut,
            "date_fin": date_fin,
            "usagers": usagers_context,
            "total_laboratoire": round(total_labo, 2),
            "logo_path": f"file://{settings.BASE_DIR}/facturation/static/facturation/images/YourUniversity.png",
        }

        rendered_html = render_to_string("facturation/facture_labo.html", context)

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmpfile:
            tmpfile_path = tmpfile.name

        HTML(string=rendered_html).write_pdf(tmpfile_path)

        with open(tmpfile_path, 'rb') as f:
            pdf_content = f.read()

        os.remove(tmpfile_path)

        nom_fichier = f"Facture_Laboratoire_{labo.replace(' ', '_')}.pdf"
        pdfs[nom_fichier] = pdf_content

    return pdfs



def get_usagers_facturables(reservation):
    """
    Retourne les usagers qui doivent être facturés pour une réservation.

    - Cas normal → l’usager lié à la réservation.
    - Cas formation → uniquement les usagers listés dans courriels_formes
      (s’ils existent dans la base Usager).
    """
    # Cas normal (réservation classique)
    if not reservation.est_formation and reservation.usager:
        return [reservation.usager]

    # Cas formation
    usagers = []
    if reservation.est_formation and reservation.courriels_formes:
        # [MODIF] Parsing robuste (virgule, point-virgule, newline)
        raw = reservation.courriels_formes
        courriels = [c.strip() for c in re.split(r'[;,\n\r]+', raw) if c.strip()]
        
        for email in courriels:
            u = Usager.objects.filter(courriel__iexact=email).first()
            if u and u not in usagers:
                usagers.append(u)
        logger.info(f"[FACTURATION] Formation {reservation.id} – {len(usagers)} usagers facturables trouvés")

    return usagers

