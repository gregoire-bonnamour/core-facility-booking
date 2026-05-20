# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

# systeme_reservation_plateforme/context_processors.py
from django.conf import settings
from urllib.parse import quote
from accounts.models import News


def support_mailto(request):
    # Récupère les emails des ADMINS (liste de tuples (name, email))
    admin_emails = [email for (_name, email) in getattr(settings, "ADMINS", []) if email]

    # Si vide, on peut fallback sur DEFAULT_FROM_EMAIL (optionnel)
    if not admin_emails and getattr(settings, "DEFAULT_FROM_EMAIL", None):
        admin_emails = [settings.DEFAULT_FROM_EMAIL]

    # Sujet demandé (sans corps)
    subject = "Plateforme cytométrie et microscopie - Signalement d'un problème"

    # Construit l’URL mailto (plusieurs destinataires séparés par des virgules)
    to_part = ",".join(admin_emails) if admin_emails else ""
    query = f"subject={quote(subject)}"  # pas de body
    mailto_url = f"mailto:{to_part}?{query}" if to_part else f"mailto:?{query}"

    return {
        "MAILTO_SIGNALER_PROBLEME": mailto_url
    }

def news_feed(request):
    return {"news_list": News.objects.filter(actif=True).order_by('-date_publication')[:5]}