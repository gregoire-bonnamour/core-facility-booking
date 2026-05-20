"""
Patch usager/views.py : ajoute la vue confirmer_activite(request, token).
Insere avant la vue accueil().
"""
import os

BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, "accounts", "views.py")

with open(path, "r", encoding="utf-8") as f:
    src = f.read()

new_vue = '''
def confirmer_activite(request, token):
    """
    Confirmation d\'activite via le lien envoye par courriel (re-verification 5 ans).
    Le token est signe avec django.core.signing (max_age=30 jours).
    """
    from django.core import signing
    from django.utils import timezone

    try:
        data = signing.loads(token, max_age=30 * 86400, salt="reverification")
        usager_id = data["usager_id"]
    except signing.SignatureExpired:
        return render(request, "usager/confirmer_activite.html", {
            "statut": "expire",
        })
    except (signing.BadSignature, KeyError):
        return render(request, "usager/confirmer_activite.html", {
            "statut": "invalide",
        })

    try:
        usager = Usager.objects.get(pk=usager_id)
    except Usager.DoesNotExist:
        return render(request, "usager/confirmer_activite.html", {
            "statut": "invalide",
        })

    if not usager.est_actif:
        return render(request, "usager/confirmer_activite.html", {
            "statut": "desactive",
        })

    usager.date_derniere_reverification = timezone.now()
    usager.save(update_fields=["date_derniere_reverification"])

    return render(request, "usager/confirmer_activite.html", {
        "statut": "ok",
        "accounts": usager,
    })


'''

old_anchor = "def accueil(request):"
assert old_anchor in src, "ERREUR: def accueil introuvable"
src = src.replace(old_anchor, new_vue + old_anchor, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(src)

print("OK: vue confirmer_activite ajoutee dans usager/views.py")
