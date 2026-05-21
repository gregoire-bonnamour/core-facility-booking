# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NoCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

"""
Commande : usagers_a_revalider

Objectif :
    1. Envoyer un email a chaque user_profile dont le profil doit etre reverifie (>= 5 ans)
       avec un lien signe (valable 30 jours) pour confirmer son activite.
    2. Envoyer un recap a l'admin listant les user_profiles contactes.

Utilisation :
    python manage.py usagers_a_revalider
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q
from django.core import signing
from django.urls import reverse

from accounts.models import UserProfile


class Command(BaseCommand):
    help = "Envoie un email de re-verification aux user_profiles >= 5 ans."

    def handle(self, *args, **options):
        seuil = timezone.now() - timezone.timedelta(days=5 * 365)

        q_due = Q(is_active=True) & (
            Q(last_reverification_date__isnull=True, activation_date__lte=seuil)
            | Q(last_reverification_date__lte=seuil)
        )

        user_profiles = (
            UserProfile.objects
            .select_related("laboratory", "affiliation")
            .filter(q_due)
            .order_by("name", "first_name")
        )

        nb = user_profiles.count()
        if nb == 0:
            self.stdout.write(self.style.SUCCESS("No user_profile a revalider."))
            return

        site_url = getattr(settings, "SITE_URL", "https://yourserver.youruniversity.ca").rstrip("/")
        from_email = settings.DEFAULT_FROM_EMAIL
        contactes = []

        for u in user_profiles:
            token = signing.dumps({"usager_id": u.pk}, salt="reverification")
            lien = site_url + reverse("accounts:confirm_activity", kwargs={"token": token})

            corps_usager = (
                f"Hello {u.first_name},\n\n"
                "Your account on the YourFacility Core Facility platform is active "
                "depuis plus de 5 ans.\n\n"
                "In order to keep our records up to date, please confirm that you "
                "still use the platform by clicking the link below:\n\n"
                f"{lien}\n\n"
                "This link is valid for 30 days. Without a response, your account "
                "sera automatiquement desactive.\n\n"
                "If you have any questions, contact the platform administrator.\n\n"
                "Bonne journee,\n"
                "Author Author -- YourFacility Core Facility"
            )

            try:
                send_mail(
                    subject="[Core Facility] Account activity confirmation (>= 5 years)",
                    message=corps_usager,
                    from_email=from_email,
                    recipient_list=[u.email],
                    fail_silently=False,
                )
                contactes.append(u)
                self.stdout.write(f"  Courriel envoye a {u.email}")
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"  ECHEC envoi a {u.email} : {e}"))

        # Recap admin
        dests_admin = [email for (_nom, email) in getattr(settings, "ADMINS", [])]
        if dests_admin and contactes:
            lignes = []
            for u in contactes:
                lab = getattr(u.laboratory, "name", "—")
                aff  = getattr(u.affiliation, "name", "—")
                date_act = u.activation_date.astimezone(timezone.get_current_timezone()).strftime("%Y-%m-%d")
                lignes.append(
                    f"- {u.name} {u.first_name} <{u.email}> | "
                    f"Affiliation: {aff} | Labo: {lab} | Activation: {date_act}"
                )

            corps_admin = (
                f"{len(contactes)} user_profile(s) ont recu un email de re-verification :\n\n"
                + "\n".join(lignes)
                + "\n\n"
                "They have 30 days to confirm their activity via the link sent.\n"
                "Sans reponse, la commande 'desactiver_non_repondants' les desactivera automatiquement."
            )
            send_mail(
                subject="[Core Facility] Re-verification sent to users",
                message=corps_admin,
                from_email=from_email,
                recipient_list=dests_admin,
                fail_silently=False,
            )

        self.stdout.write(self.style.SUCCESS(
            f"Termine : {len(contactes)}/{nb} email(s) envoye(s)."
        ))
