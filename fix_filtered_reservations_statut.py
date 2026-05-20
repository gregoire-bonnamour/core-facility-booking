"""
Patch _filtered_reservations pour inclure les reservations terminees aujourd'hui
meme si le cron n'a pas encore mis a day_of_week leur status a 'past'.
"""
import os

BASE = os.path.dirname(os.path.abspath(__file__))
views_path = os.path.join(BASE, "booking", "views.py")

with open(views_path, "r", encoding="utf-8") as f:
    src = f.read()

old_block = (
    "def _filtered_reservations(filters):\n"
    "    \"\"\"\n"
    "    S\u00e9lectionne les r\u00e9servations qui chevauchent la p\u00e9riode (si fournie),\n"
    "    filtr\u00e9es par les cases coch\u00e9es. Statuts par d\u00e9faut: seulement 'past'.\n"
    "    \"\"\"\n"
    "    qs = (Reservation.objects\n"
    "          .select_related('usager__laboratoire__affiliation', 'usager__fonction', 'equipment')\n"
    "          .filter(status='past'))"
)
new_block = (
    "def _filtered_reservations(filters):\n"
    "    \"\"\"\n"
    "    S\u00e9lectionne les r\u00e9servations qui chevauchent la p\u00e9riode (si fournie),\n"
    "    filtr\u00e9es par les cases coch\u00e9es.\n"
    "    Inclut les r\u00e9servations physiquement termin\u00e9es (date/heure fin pass\u00e9e)\n"
    "    m\u00eame si le cron n'a pas encore mis 'past'.\n"
    "    \"\"\"\n"
    "    _today = date.today()\n"
    "    _now_time = datetime.now().time()\n"
    "    qs = (Reservation.objects\n"
    "          .select_related('usager__laboratoire__affiliation', 'usager__fonction', 'equipment')\n"
    "          .exclude(status='cancelled')\n"
    "          .filter(\n"
    "              Q(status='past')\n"
    "              | Q(end_date__lt=_today)\n"
    "              | Q(end_date=_today, end_time__lte=_now_time)\n"
    "          ))"
)

assert old_block in src, "ERREUR: bloc _filtered_reservations introuvable"
src = src.replace(old_block, new_block, 1)

with open(views_path, "w", encoding="utf-8") as f:
    f.write(src)

print("OK: _filtered_reservations corrige (inclut reservations terminees hors cron)")
