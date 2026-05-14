"""
Patch stats_query : nb_formations compte les personnes formees (Invitation validee)
plutot que les sessions de formation (Reservation.est_formation).
"""
import os

BASE = os.path.dirname(os.path.abspath(__file__))
views_path = os.path.join(BASE, "reserv", "views.py")

with open(views_path, "r", encoding="utf-8") as f:
    src = f.read()

# 1. Supprimer nb_form = 0 de l'initialisation
old_init = (
    "    nb_form = 0\n"
    "    usagers_distincts = set()\n"
    "    demandes_exception = 0"
)
new_init = (
    "    usagers_distincts = set()\n"
    "    demandes_exception = 0"
)
assert old_init in src, "ERREUR: init nb_form introuvable"
src = src.replace(old_init, new_init, 1)
print("OK: nb_form = 0 supprime de l'init")

# 2. Remplacer nb_form += 1; continue par juste continue dans le loop
old_loop = (
    "        if getattr(r, 'est_formation', False):\n"
    "            nb_form += 1\n"
    "            continue"
)
new_loop = (
    "        if getattr(r, 'est_formation', False):\n"
    "            continue"
)
assert old_loop in src, "ERREUR: bloc est_formation dans loop introuvable"
src = src.replace(old_loop, new_loop, 1)
print("OK: nb_form += 1 supprime du loop")

# 3. Calculer nb_form apres le loop, avant kpis = {
old_kpis = (
    "    kpis = {\n"
    "        'reservations': total_reservations,"
)
new_kpis = (
    "    from usager.models import Invitation\n"
    "    _form_resa_ids = [r.pk for r in resas if r.est_formation]\n"
    "    nb_form = Invitation.objects.filter(\n"
    "        reservation_id__in=_form_resa_ids,\n"
    "        date_validation__isnull=False,\n"
    "    ).count()\n"
    "\n"
    "    kpis = {\n"
    "        'reservations': total_reservations,"
)
assert old_kpis in src, "ERREUR: kpis = { introuvable"
src = src.replace(old_kpis, new_kpis, 1)
print("OK: calcul nb_form via Invitation ajoute avant kpis")

with open(views_path, "w", encoding="utf-8") as f:
    f.write(src)

print("OK: views.py sauvegarde")
