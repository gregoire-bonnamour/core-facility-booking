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
            lien = site_url + reverse("accounts:confirmer_activite", kwargs={"token": token})

            corps_usager = (
                f"Bonjour {u.first_name},\n\n"
                "Votre compte sur la Plateforme Cellulaire YourUniversity (YourFacility) est is_active "
                "depuis plus de 5 ans.\n\n"
                "Afin de maintenir notre registre a day_of_week, merci de confirmer que vous "
                "utilisez toujours la plateforme en cliquant sur le lien ci-dessous :\n\n"
                f"{lien}\n\n"
                "Ce lien est valable 30 jours. Sans reponse de votre part, votre compte "
                "sera automatiquement desactive.\n\n"
                "Si vous avez des questions, contactez l'administrateur de la plateforme.\n\n"
                "Bonne journee,\n"
                "Author Author -- Plateforme Cellulaire YourUniversity (YourFacility)"
            )

            try:
                send_mail(
                    subject="[Plateforme cellulaire] Confirmation de votre compte (>= 5 ans)",
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
                "Ils ont 30 jours pour confirmer leur activite via le lien envoye.\n"
                "Sans reponse, la commande 'desactiver_non_repondants' les desactivera automatiquement."
            )
            send_mail(
                subject="[Plateforme cellulaire] Re-verification envoyee a des user_profiles",
                message=corps_admin,
                from_email=from_email,
                recipient_list=dests_admin,
                fail_silently=False,
            )

        self.stdout.write(self.style.SUCCESS(
            f"Termine : {len(contactes)}/{nb} email(s) envoye(s)."
        ))
