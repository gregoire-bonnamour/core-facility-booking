"""
Patch middleware.py : ajouter la mise a jour des reservations
terminees aujourd'hui (date_fin = today ET heure_fin <= maintenant).
"""
import os

BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, "booking", "middleware.py")

with open(path, "r", encoding="utf-8") as f:
    src = f.read()

old_block = (
    "        if cache.add('statuts_updated', True, 60):\n"
    "            aujourd_hui = timezone.localdate()\n"
    "            (Reservation.objects\n"
    "                .filter(date_fin__lt=aujourd_hui)\n"
    "                .exclude(statut__in=['passee', 'annulee'])\n"
    "                .update(statut='passee'))\n"
    "        return self.get_response(request)"
)
new_block = (
    "        if cache.add('statuts_updated', True, 60):\n"
    "            aujourd_hui = timezone.localdate()\n"
    "            maintenant  = timezone.localtime().time()\n"
    "            # Reservations terminees avant aujourd'hui\n"
    "            (Reservation.objects\n"
    "                .filter(date_fin__lt=aujourd_hui)\n"
    "                .exclude(statut__in=['passee', 'annulee'])\n"
    "                .update(statut='passee'))\n"
    "            # Reservations terminees aujourd'hui (heure_fin passee)\n"
    "            (Reservation.objects\n"
    "                .filter(date_fin=aujourd_hui, heure_fin__lte=maintenant)\n"
    "                .exclude(statut__in=['passee', 'annulee'])\n"
    "                .update(statut='passee'))\n"
    "        return self.get_response(request)"
)

assert old_block in src, "ERREUR: bloc middleware introuvable"
src = src.replace(old_block, new_block, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(src)

print("OK: middleware mis a jour (inclut reservations terminees aujourd'hui)")
