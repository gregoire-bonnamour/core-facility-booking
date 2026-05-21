"""
Patch middleware.py : ajouter la mise a day_of_week des reservations
terminees aujourd'hui (end_date = today ET end_time <= maintenant).
"""
import os

BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, "booking", "middleware.py")

with open(path, "r", encoding="utf-8") as f:
    src = f.read()

old_block = (
    "        if cache.add('statuses_updated', True, 60):\n"
    "            aujourd_hui = timezone.localdate()\n"
    "            (Reservation.objects\n"
    "                .filter(end_date__lt=aujourd_hui)\n"
    "                .exclude(status__in=['past', 'cancelled'])\n"
    "                .update(status='past'))\n"
    "        return self.get_response(request)"
)
new_block = (
    "        if cache.add('statuses_updated', True, 60):\n"
    "            aujourd_hui = timezone.localdate()\n"
    "            maintenant  = timezone.localtime().time()\n"
    "            # Reservations terminees avant aujourd'hui\n"
    "            (Reservation.objects\n"
    "                .filter(end_date__lt=aujourd_hui)\n"
    "                .exclude(status__in=['past', 'cancelled'])\n"
    "                .update(status='past'))\n"
    "            # Reservations terminees aujourd'hui (end_time passee)\n"
    "            (Reservation.objects\n"
    "                .filter(end_date=aujourd_hui, end_time__lte=maintenant)\n"
    "                .exclude(status__in=['past', 'cancelled'])\n"
    "                .update(status='past'))\n"
    "        return self.get_response(request)"
)

assert old_block in src, "ERREUR: bloc middleware introuvable"
src = src.replace(old_block, new_block, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(src)

print("OK: middleware mis a day_of_week (inclut reservations terminees aujourd'hui)")
