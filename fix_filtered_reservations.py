"""
Patch _filtered_reservations pour utiliser .get() au lieu de [] sur les cles absentes.
"""
import os

BASE = os.path.dirname(os.path.abspath(__file__))
views_path = os.path.join(BASE, "reserv", "views.py")

with open(views_path, "r", encoding="utf-8") as f:
    src = f.read()

old_block = (
    "    if filters['equipements']:\n"
    "        qs = qs.filter(equipement_id__in=filters['equipements'])\n"
    "    if filters['affiliations']:\n"
    "        qs = qs.filter(usager__laboratoire__affiliation_id__in=filters['affiliations'])\n"
    "    if filters['laboratoires']:\n"
    "        qs = qs.filter(usager__laboratoire_id__in=filters['laboratoires'])\n"
    "    if filters['fonctions']:\n"
    "        qs = qs.filter(usager__fonction_id__in=filters['fonctions'])\n"
    "    if filters['usagers']:\n"
    "        qs = qs.filter(usager_id__in=filters['usagers'])\n"
    "\n"
    "    return qs"
)
new_block = (
    "    if filters.get('equipements'):\n"
    "        qs = qs.filter(equipement_id__in=filters['equipements'])\n"
    "    if filters.get('affiliations'):\n"
    "        qs = qs.filter(usager__laboratoire__affiliation_id__in=filters['affiliations'])\n"
    "    if filters.get('laboratoires'):\n"
    "        qs = qs.filter(usager__laboratoire_id__in=filters['laboratoires'])\n"
    "    if filters.get('fonctions'):\n"
    "        qs = qs.filter(usager__fonction_id__in=filters['fonctions'])\n"
    "    if filters.get('usagers'):\n"
    "        qs = qs.filter(usager_id__in=filters['usagers'])\n"
    "\n"
    "    return qs"
)

assert old_block in src, "ERREUR: bloc _filtered_reservations introuvable"
src = src.replace(old_block, new_block, 1)

with open(views_path, "w", encoding="utf-8") as f:
    f.write(src)

print("OK: _filtered_reservations corrige (.get() au lieu de [])")
