"""
Patch views.py : nb_formations compte les personnes formees (Invitation validee)
dans _agg_metrics (Excel par equipement) et dans le dashboard Excel stats.
"""
import os

BASE = os.path.dirname(os.path.abspath(__file__))
views_path = os.path.join(BASE, "booking", "views.py")

with open(views_path, "r", encoding="utf-8") as f:
    src = f.read()

# ── 1. _agg_metrics : collecter les PKs pendant le loop, calculer apres ──────
old_agg = (
    "    nb_form = 0   # \U0001f448 unique compteur formations\n"
    "\n"
    "    for r in reservations:\n"
    "        n += 1\n"
    "        u,a = _minutes_usage_assistance(r)\n"
    "        min_usage += u\n"
    "        min_ass   += a\n"
    "        if r.usager_id:\n"
    "            users.add(r.usager_id)\n"
    "        if r.assistance:\n"
    "            nb_ass += 1\n"
    "        if r.est_formation:\n"
    "            nb_form += 1\n"
    "\n"
    "    total_min = min_usage + min_ass"
)
new_agg = (
    "    _form_pks = []\n"
    "    for r in reservations:\n"
    "        n += 1\n"
    "        u,a = _minutes_usage_assistance(r)\n"
    "        min_usage += u\n"
    "        min_ass   += a\n"
    "        if r.usager_id:\n"
    "            users.add(r.usager_id)\n"
    "        if r.assistance:\n"
    "            nb_ass += 1\n"
    "        if r.est_formation:\n"
    "            _form_pks.append(r.pk)\n"
    "\n"
    "    nb_form = Invitation.objects.filter(\n"
    "        reservation_id__in=_form_pks,\n"
    "        date_validation__isnull=False,\n"
    "    ).count() if _form_pks else 0\n"
    "\n"
    "    total_min = min_usage + min_ass"
)
assert old_agg in src, "ERREUR: bloc _agg_metrics introuvable"
src = src.replace(old_agg, new_agg, 1)
print("OK: _agg_metrics corrige")

# ── 2. Dashboard Excel : init ─────────────────────────────────────────────────
old_init = (
    "    nb_formations = 0\n"
    "    nb_assistances = 0"
)
new_init = (
    "    _form_pks_dash = []\n"
    "    nb_assistances = 0"
)
assert old_init in src, "ERREUR: init nb_formations dashboard introuvable"
src = src.replace(old_init, new_init, 1)
print("OK: init nb_formations dashboard supprime")

# ── 3. Dashboard Excel : loop ─────────────────────────────────────────────────
old_loop = (
    "        if r.est_formation:\n"
    "            type_resa = \"Formation\"\n"
    "            data_by_type['Formation'] += duree_h\n"
    "            nb_formations += 1"
)
new_loop = (
    "        if r.est_formation:\n"
    "            type_resa = \"Formation\"\n"
    "            data_by_type['Formation'] += duree_h\n"
    "            _form_pks_dash.append(r.pk)"
)
assert old_loop in src, "ERREUR: bloc loop nb_formations dashboard introuvable"
src = src.replace(old_loop, new_loop, 1)
print("OK: loop dashboard corrige")

# ── 4. Dashboard Excel : calcul apres le loop ─────────────────────────────────
old_phase2 = (
    "    # ============================================================================\n"
    "    # PHASE 2: Remplissage de l'onglet \"Donn\u00e9es Brutes\"\n"
    "    # ============================================================================"
)
new_phase2 = (
    "    nb_formations = Invitation.objects.filter(\n"
    "        reservation_id__in=_form_pks_dash,\n"
    "        date_validation__isnull=False,\n"
    "    ).count() if _form_pks_dash else 0\n"
    "\n"
    "    # ============================================================================\n"
    "    # PHASE 2: Remplissage de l'onglet \"Donn\u00e9es Brutes\"\n"
    "    # ============================================================================"
)
assert old_phase2 in src, "ERREUR: PHASE 2 introuvable"
src = src.replace(old_phase2, new_phase2, 1)
print("OK: calcul nb_formations dashboard ajoute apres le loop")

with open(views_path, "w", encoding="utf-8") as f:
    f.write(src)
print("OK: views.py sauvegarde")
