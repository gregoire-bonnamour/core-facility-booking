"""
Patch user_profile/urls.py : ajoute l'URL confirmer-activite/<token>/.
"""
import os

BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, "accounts", "urls.py")

with open(path, "r", encoding="utf-8") as f:
    src = f.read()

old_anchor = "    # Reglement\n    path(\"reglement/\","
new_anchor = (
    "    # Re-verification 5 ans\n"
    "    path('confirmer-activite/<str:token>/', views.confirmer_activite, name='confirmer_activite'),\n"
    "\n"
    "    # Reglement\n"
    "    path(\"reglement/\","
)

assert old_anchor in src, "ERREUR: ancre Reglement introuvable dans urls.py"
src = src.replace(old_anchor, new_anchor, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(src)

print("OK: URL confirmer-activite ajoutee dans user_profile/urls.py")
