"""
Demo seed script for core-facility-booking.
Deletes existing DB, runs migrations, and populates a realistic week of data.

Run from project root:
    python seed_demo.py
"""

import os, sys, subprocess, django
from datetime import date, time, timedelta

ROOT = "/home/gregoire/apps/core-facility-booking"
os.chdir(ROOT)
sys.path.insert(0, ROOT)
os.environ["DJANGO_SETTINGS_MODULE"] = "systeme_reservation_plateforme.settings.local"

# ── 1. Fresh DB ────────────────────────────────────────────────────────────────
db_path = os.path.join(ROOT, "db.sqlite3")
if os.path.exists(db_path):
    os.remove(db_path)
    print("Deleted old db.sqlite3")

subprocess.run([sys.executable, "manage.py", "migrate", "--run-syncdb"], check=True)
print("Migrations applied.\n")

django.setup()

from django.contrib.auth.models import User
from accounts.models import Affiliation, Laboratory, Role, UserProfile, Invitation
from equipment.models import Equipment, TimeSlot, UsageQuota, Rate, TrainingRate
from booking.models import Reservation

# ── 2. Affiliations ────────────────────────────────────────────────────────────
aff_univ, _ = Affiliation.objects.get_or_create(
    name="YourUniversity",
    defaults={"assistance_rate": 0}
)
aff_mcgill, _ = Affiliation.objects.get_or_create(
    name="McGill University",
    defaults={"assistance_rate": 0}
)
aff_industry, _ = Affiliation.objects.get_or_create(
    name="InnovateBio Inc.",
    defaults={"assistance_rate": 75}
)

# ── 3. Laboratories ────────────────────────────────────────────────────────────
lab_bioimaging, _ = Laboratory.objects.get_or_create(
    name="BioImaging Lab", affiliation=aff_univ
)
lab_neuro, _ = Laboratory.objects.get_or_create(
    name="Neuroscience Lab", affiliation=aff_univ
)
lab_mcgill, _ = Laboratory.objects.get_or_create(
    name="Biostatistics Group", affiliation=aff_mcgill
)
lab_industry, _ = Laboratory.objects.get_or_create(
    name="InnovateBio Corp", affiliation=aff_industry
)

# ── 4. Roles ───────────────────────────────────────────────────────────────────
role_phd,    _ = Role.objects.get_or_create(name="PhD Student")
role_postdoc,_ = Role.objects.get_or_create(name="Postdoc")
role_res,    _ = Role.objects.get_or_create(name="Researcher")
role_prof,   _ = Role.objects.get_or_create(name="Professor")

# ── 5. Equipment ───────────────────────────────────────────────────────────────
confocal, _ = Equipment.objects.get_or_create(
    name="Confocal Microscope A",
    defaults={
        "description": "Leica SP8 confocal laser scanning microscope. "
                       "Ideal for high-resolution 3D imaging of fixed and live samples. "
                       "Equipped with 405, 488, 561 and 633 nm laser lines.",
        "type": "microscope",
        "location": "Room 201",
        "max_duration_hours": 8,
        "is_active": True,
    }
)

cytometer, _ = Equipment.objects.get_or_create(
    name="Flow Cytometer B",
    defaults={
        "description": "BD FACSAria III cell sorter. "
                       "Up to 13 fluorescence channels. "
                       "Capable of high-speed cell sorting up to 25,000 events/sec.",
        "type": "cytomètre",
        "location": "Room 103",
        "max_duration_hours": 6,
        "is_active": True,
    }
)

analyzer, _ = Equipment.objects.get_or_create(
    name="Image Analyzer C",
    defaults={
        "description": "Cellomics ArrayScan automated high-content imaging system. "
                       "No prior training required. "
                       "Plate-based imaging for phenotypic screening.",
        "type": "analyse",
        "location": "Room 305",
        "max_duration_hours": 12,
        "is_active": True,
    }
)

# ── 6. Time slots ─────────────────────────────────────────────────────────────
# Confocal: Mon–Fri, morning + afternoon blocks
for day in range(5):
    TimeSlot.objects.get_or_create(equipment=confocal, day_of_week=day,
        start_time=time(8, 0), end_time=time(12, 0))
    TimeSlot.objects.get_or_create(equipment=confocal, day_of_week=day,
        start_time=time(13, 0), end_time=time(17, 0))

# Cytometer: Tue + Thu
for day in [1, 3]:
    TimeSlot.objects.get_or_create(equipment=cytometer, day_of_week=day,
        start_time=time(9, 0), end_time=time(17, 0))

# Analyzer: Mon, Wed, Fri
for day in [0, 2, 4]:
    TimeSlot.objects.get_or_create(equipment=analyzer, day_of_week=day,
        start_time=time(8, 0), end_time=time(18, 0))

# ── 7. Usage quotas (confocal: max 4h/day in peak hours) ──────────────────────
for day in range(5):
    UsageQuota.objects.get_or_create(
        equipment=confocal,
        day_of_week=day,
        start_time=time(9, 0),
        end_time=time(13, 0),
        defaults={"max_duration_minutes": 240},
    )

# ── 8. Rates ───────────────────────────────────────────────────────────────────
for equip, univ_rate, ext_rate in [
    (confocal,  25, 60),
    (cytometer, 30, 70),
    (analyzer,  15, 40),
]:
    Rate.objects.get_or_create(equipment=equip, affiliation=aff_univ,
                               defaults={"hourly_rate": univ_rate})
    Rate.objects.get_or_create(equipment=equip, affiliation=aff_mcgill,
                               defaults={"hourly_rate": ext_rate})
    Rate.objects.get_or_create(equipment=equip, affiliation=aff_industry,
                               defaults={"hourly_rate": ext_rate})

for equip, fee in [(confocal, 150), (cytometer, 200)]:
    TrainingRate.objects.get_or_create(equipment=equip, affiliation=aff_univ,
                                       defaults={"training_fee": fee})
    TrainingRate.objects.get_or_create(equipment=equip, affiliation=aff_mcgill,
                                       defaults={"training_fee": fee + 50})

# ── 9. Admin user ──────────────────────────────────────────────────────────────
admin_user, _ = User.objects.get_or_create(username="admin",
                                           defaults={"email": "admin@youruniversity.ca",
                                                     "is_staff": True, "is_superuser": True})
admin_user.set_password("demo1234")
admin_user.save()

admin_profile, _ = UserProfile.objects.get_or_create(user=admin_user)
admin_profile.first_name = "Admin"
admin_profile.name = "Platform"
admin_profile.email = "admin@youruniversity.ca"
admin_profile.is_active = True
admin_profile.is_platform_admin = True
admin_profile.terms_accepted = True
admin_profile.laboratory = lab_bioimaging
admin_profile.affiliation = aff_univ
admin_profile.role = role_prof
admin_profile.save()
admin_profile.authorized_equipment.set([confocal, cytometer, analyzer])

# ── 10. Regular users ──────────────────────────────────────────────────────────
def make_user(username, password, first_name, last_name, email,
              role, affiliation, laboratory, equipment_list, is_admin=False):
    u, _ = User.objects.get_or_create(username=username,
                                      defaults={"email": email})
    u.set_password(password)
    u.save()
    # get_or_create with defaults fails silently if the signal already created
    # the profile (with laboratory=None). Always set fields explicitly.
    p, _ = UserProfile.objects.get_or_create(user=u)
    p.first_name = first_name
    p.name = last_name
    p.email = email
    p.is_active = True
    p.is_platform_admin = is_admin
    p.terms_accepted = True
    p.role = role
    p.affiliation = affiliation
    p.laboratory = laboratory
    p.save()
    p.authorized_equipment.set(equipment_list)
    return u, p

_, alice   = make_user("alice",  "demo1234", "Alice",  "Researcher",
                       "alice@youruniversity.ca",
                       role_postdoc, aff_univ, lab_bioimaging,
                       [confocal, cytometer, analyzer])

_, bob     = make_user("bob",    "demo1234", "Bob",    "Student",
                       "bob@youruniversity.ca",
                       role_phd, aff_univ, lab_neuro,
                       [confocal, cytometer, analyzer])

_, chen    = make_user("chenwei","demo1234", "Chen",   "Wei",
                       "chen.wei@mcgill.ca",
                       role_res, aff_mcgill, lab_mcgill,
                       [cytometer, analyzer])

_, emma    = make_user("emma",   "demo1234", "Emma",   "Johnson",
                       "emma@youruniversity.ca",
                       role_phd, aff_univ, lab_bioimaging,
                       [confocal, analyzer])

_, marc    = make_user("marc",   "demo1234", "Marc",   "Dubois",
                       "marc.dubois@innovatebio.com",
                       role_postdoc, aff_industry, lab_industry,
                       [cytometer, analyzer])

# ── 11. Reservations — week of May 18–23, 2026 ────────────────────────────────
# We set start_date/end_date and times; status is auto-managed by model.save()
# Use force_status=True so auto-recalc doesn't flip everything to "past".

def book(equip, user_profile, d, h_start, h_end, **kwargs):
    """Create a reservation with force_status to preserve 'upcoming'."""
    r = Reservation(
        equipment=equip,
        user_profile=user_profile,
        start_date=d,
        end_date=d,
        start_time=time(h_start, 0),
        end_time=time(h_end, 0),
        status="upcoming",
        **kwargs
    )
    r.save(force_status=True, skip_invitations=True)
    return r

MON = date(2026, 5, 18)
TUE = date(2026, 5, 19)
WED = date(2026, 5, 20)
THU = date(2026, 5, 21)
FRI = date(2026, 5, 22)

# ── Monday ─────────────────────────────────────────────────────────────────────
book(confocal,  alice, MON, 10, 12)
book(cytometer, bob,   MON, 14, 17)
book(analyzer,  marc,  MON,  9, 11)
book(analyzer,  alice, MON, 13, 16)

# ── Tuesday ────────────────────────────────────────────────────────────────────
book(confocal,  chen,  TUE,  9, 12)
book(cytometer, bob,   TUE,  9, 11)
book(cytometer, marc,  TUE, 13, 16)
book(analyzer,  emma,  TUE, 10, 12)
book(analyzer,  bob,   TUE, 14, 16)

# Training session: Alice trains Emma on Confocal (afternoon)
training = book(
    confocal, alice, TUE, 13, 17,
    is_training=True,
    trained_emails="emma@youruniversity.ca",
)

# ── Wednesday ──────────────────────────────────────────────────────────────────
book(cytometer, chen,  WED,  9, 11)
book(confocal,  alice, WED, 10, 12)
book(analyzer,  bob,   WED,  9, 11)
book(analyzer,  chen,  WED, 13, 15)
book(cytometer, alice, WED, 14, 16)
book(confocal,  marc,  WED, 14, 17)

# ── Thursday ───────────────────────────────────────────────────────────────────
book(confocal,  bob,   THU, 10, 12)
book(cytometer, emma,  THU, 10, 12)
book(analyzer,  marc,  THU, 10, 12)
book(cytometer, bob,   THU, 14, 16)
book(analyzer,  alice, THU, 14, 17)

# Maintenance block on Confocal Thursday afternoon
maint = book(
    confocal, admin_profile, THU, 15, 18,
    is_maintenance=True,
)

# ── Friday ─────────────────────────────────────────────────────────────────────
book(cytometer, chen,  FRI,  8, 10)
book(confocal,  marc,  FRI, 10, 12)
book(analyzer,  emma,  FRI,  9, 11)
book(cytometer, alice, FRI, 13, 15)
book(analyzer,  bob,   FRI, 13, 15)
book(confocal,  emma,  FRI, 14, 16)

# One pending (exception request) — Bob wants Friday evening on confocal
pending_r = book(
    confocal, bob, FRI, 17, 20,
    exception_request=True,
    justification="Need extra time to finish imaging for thesis deadline.",
)
pending_r.status = "pending"
pending_r.save(force_status=True, skip_invitations=True)

# ── Summary ────────────────────────────────────────────────────────────────────
print(f"\n✓ Created:")
print(f"  {Affiliation.objects.count()} affiliations")
print(f"  {Laboratory.objects.count()} laboratories")
print(f"  {Role.objects.count()} roles")
print(f"  {Equipment.objects.count()} equipment items")
print(f"  {TimeSlot.objects.count()} time slots")
print(f"  {UserProfile.objects.count()} user profiles")
print(f"  {Reservation.objects.count()} reservations")
print(f"\nAdmin login: admin / demo1234")
print(f"App URL:     http://localhost:8001")
