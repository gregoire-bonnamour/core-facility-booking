# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

import random
from datetime import date, time, datetime, timedelta
from booking.models import Reservation
from accounts.models import UserProfile
from equipment.models import Equipment

random.seed(42)  # reproductible

# Récupération des objets existants
usagers = list(UserProfile.objects.all())
equipment_set = list(
    Equipment.objects.filter(nom__in=["CYTOFlex", "Stellaris 8 FALCON STED (Leica)"])
)

if not usagers or not equipment_set:
    print("⚠️ Pas assez de données existantes (usagers et équipements requis).")
else:
    print(f"✅ {len(usagers)} usagers et {len(equipment_set)} équipements trouvés")

# Option : nettoyer les réservations de test avant génération
# Reservation.objects.all().delete()

def random_time():
    heure = random.randint(8, 18)  # heures de journée
    minute = random.choice([0, 30])
    return time(heure, minute)

def random_duration():
    return timedelta(hours=random.randint(1, 4))

nb_reservations = 200

for _ in range(nb_reservations):
    user_profile = random.choice(usagers)
    equipment = random.choice(equipment_set)

    # Période : uniquement sur les 60 derniers jours
    start_date = date.today() - timedelta(days=random.randint(0, 60))

    start_time = random_time()
    duration = random_duration()
    end_time = (datetime.combine(start_date, start_time) + duration).time()

    resa_type = random.choice(["classique", "assistance", "formation"])

    kwargs = {
        "accounts": user_profile,
        "equipment": equipment,
        "start_date": start_date,
        "end_date": start_date,
        "start_time": start_time,
        "end_time": end_time,
    }

    if resa_type == "assistance":
        kwargs.update({
            "assistance": True,
            "assistance_duration_minutes": random.choice([30, 60, 90, 120]),
        })
    elif resa_type == "formation":
        participants = random.sample(usagers, k=min(len(usagers), random.randint(2, 5)))
        emails = ",".join(u.email for u in participants if u.email)
        kwargs.update({
            "is_training": True,
            "trained_emails": emails,
        })

    Reservation.objects.create(**kwargs)

print(f"🎉 Généré {nb_reservations} réservations variées (2 derniers mois) sur {len(equipment_set)} équipements")
