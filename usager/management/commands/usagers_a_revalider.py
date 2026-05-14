# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

"""
Commande : usagers_a_revalider

Objectif :
    1. Envoyer un courriel a chaque usager dont le profil doit etre reverifie (>= 5 ans)
       avec un lien signe (valable 30 jours) pour confirmer son activite.
    2. Envoyer un recap a l'admin listant les usagers contactes.

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

from usager.models import Usager


class Command(BaseCommand):
    help = "Envoie un courriel de re-verification aux usagers >= 5 ans."

    def handle(self, *args, **options):
        seuil = timezone.now() - timezone.timedelta(days=5 * 365)

        q_due = Q(est_actif=True) & (
            Q(date_derniere_reverification__isnull=True, date_activation__lte=seuil)
            | Q(date_derniere_reverification__lte=seuil)
        )

        usagers = (
            Usager.objects
            .select_related("laboratoire", "affiliation")
            .filter(q_due)
            .order_by("nom", "prenom")
        )

        nb = usagers.count()
        if nb == 0:
            self.stdout.write(self.style.SUCCESS("Aucun usager a revalider."))
            return

        site_url = getattr(settings, "SITE_URL", "https://yourserver.youruniversity.ca").rstrip("/")
        from_email = settings.DEFAULT_FROM_EMAIL
        contactes = []

        for u in usagers:
            token = signing.dumps({"usager_id": u.pk}, salt="reverification")
            lien = site_url + reverse("usager:confirmer_activite", kwargs={"token": token})

            corps_usager = (
                f"Bonjour {u.prenom},\n\n"
                "Votre compte sur la Plateforme Cellulaire YourUniversity (YourFacility) est actif "
                "depuis plus de 5 ans.\n\n"
                "Afin de maintenir notre registre a jour, merci de confirmer que vous "
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
                    recipient_list=[u.courriel],
                    fail_silently=False,
                )
                contactes.append(u)
                self.stdout.write(f"  Courriel envoye a {u.courriel}")
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"  ECHEC envoi a {u.courriel} : {e}"))

        # Recap admin
        dests_admin = [email for (_nom, email) in getattr(settings, "ADMINS", [])]
        if dests_admin and contactes:
            lignes = []
            for u in contactes:
                labo = getattr(u.laboratoire, "nom", "—")
                aff  = getattr(u.affiliation, "nom", "—")
                date_act = u.date_activation.astimezone(timezone.get_current_timezone()).strftime("%Y-%m-%d")
                lignes.append(
                    f"- {u.nom} {u.prenom} <{u.courriel}> | "
                    f"Affiliation: {aff} | Labo: {labo} | Activation: {date_act}"
                )

            corps_admin = (
                f"{len(contactes)} usager(s) ont recu un courriel de re-verification :\n\n"
                + "\n".join(lignes)
                + "\n\n"
                "Ils ont 30 jours pour confirmer leur activite via le lien envoye.\n"
                "Sans reponse, la commande 'desactiver_non_repondants' les desactivera automatiquement."
            )
            send_mail(
                subject="[Plateforme cellulaire] Re-verification envoyee a des usagers",
                message=corps_admin,
                from_email=from_email,
                recipient_list=dests_admin,
                fail_silently=False,
            )

        self.stdout.write(self.style.SUCCESS(
            f"Termine : {len(contactes)}/{nb} courriel(s) envoye(s)."
        ))
