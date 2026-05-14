"""
Patch _filtered_reservations pour inclure les reservations terminees aujourd'hui
meme si le cron n'a pas encore mis a jour leur statut a 'passee'.
"""
import os

BASE = os.path.dirname(os.path.abspath(__file__))
views_path = os.path.join(BASE, "reserv", "views.py")

with open(views_path, "r", encoding="utf-8") as f:
    src = f.read()

old_block = (
    "def _filtered_reservations(filters):\n"
    "    \"\"\"\n"
    "    S\u00e9lectionne les r\u00e9servations qui chevauchent la p\u00e9riode (si fournie),\n"
    "    filtr\u00e9es par les cases coch\u00e9es. Statuts par d\u00e9faut: seulement 'passee'.\n"
    "    \"\"\"\n"
    "    qs = (Reservation.objects\n"
    "          .select_related('usager__laboratoire__affiliation', 'usager__fonction', 'equipement')\n"
    "          .filter(statut='passee'))"
)
new_block = (
    "def _filtered_reservations(filters):\n"
    "    \"\"\"\n"
    "    S\u00e9lectionne les r\u00e9servations qui chevauchent la p\u00e9riode (si fournie),\n"
    "    filtr\u00e9es par les cases coch\u00e9es.\n"
    "    Inclut les r\u00e9servations physiquement termin\u00e9es (date/heure fin pass\u00e9e)\n"
    "    m\u00eame si le cron n'a pas encore mis 'passee'.\n"
    "    \"\"\"\n"
    "    _today = date.today()\n"
    "    _now_time = datetime.now().time()\n"
    "    qs = (Reservation.objects\n"
    "          .select_related('usager__laboratoire__affiliation', 'usager__fonction', 'equipement')\n"
    "          .exclude(statut='annulee')\n"
    "          .filter(\n"
    "              Q(statut='passee')\n"
    "              | Q(date_fin__lt=_today)\n"
    "              | Q(date_fin=_today, heure_fin__lte=_now_time)\n"
    "          ))"
)

assert old_block in src, "ERREUR: bloc _filtered_reservations introuvable"
src = src.replace(old_block, new_block, 1)

with open(views_path, "w", encoding="utf-8") as f:
    f.write(src)

print("OK: _filtered_reservations corrige (inclut reservations terminees hors cron)")
