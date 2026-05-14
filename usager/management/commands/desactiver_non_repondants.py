# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

"""
Commande : desactiver_non_repondants

Objectif :
    Desactiver les usagers qui n'ont pas confirme leur activite dans les 30 jours
    suivant l'envoi du courriel de re-verification (usagers_a_revalider).

    Logique : un usager est concerne si :
      - il est encore actif
      - son seuil de re-verification est depasse depuis >= 5 ans + 30 jours
        (c'est-a-dire que usagers_a_revalider aurait du lui envoyer un courriel
         il y a au moins 30 jours, et il n'a pas clique)

    Si la commande usagers_a_revalider tourne le 31 janvier,
    desactiver_non_repondants doit tourner 30 jours plus tard (environ le 2 mars).

Utilisation :
    python manage.py desactiver_non_repondants
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q

from usager.models import Usager


class Command(BaseCommand):
    help = "Desactive les usagers qui n'ont pas repondu au courriel de re-verification (>= 30j)."

    def handle(self, *args, **options):
        # Seuil : 5 ans + 30 jours (le courriel a ete envoye il y a 30j min)
        seuil = timezone.now() - timezone.timedelta(days=5 * 365 + 30)

        q_due = Q(est_actif=True) & (
            Q(date_derniere_reverification__isnull=True, date_activation__lte=seuil)
            | Q(date_derniere_reverification__lte=seuil)
        )

        usagers = (
            Usager.objects
            .select_related("laboratoire", "affiliation", "user")
            .filter(q_due)
            .order_by("nom", "prenom")
        )

        nb = usagers.count()
        if nb == 0:
            self.stdout.write(self.style.SUCCESS("Aucun usager a desactiver."))
            return

        desactives = []
        for u in usagers:
            u.est_actif = False
            u.save(update_fields=["est_actif"])
            # Desactiver aussi le User Django pour bloquer la connexion
            if hasattr(u, "user") and u.user:
                u.user.is_active = False
                u.user.save(update_fields=["is_active"])
            desactives.append(u)
            self.stdout.write(f"  Desactive : {u.nom} {u.prenom} <{u.courriel}>")

        # Notifier l'admin
        dests_admin = [email for (_nom, email) in getattr(settings, "ADMINS", [])]
        if dests_admin:
            lignes = []
            for u in desactives:
                labo = getattr(u.laboratoire, "nom", "—")
                aff  = getattr(u.affiliation, "nom", "—")
                date_act = u.date_activation.astimezone(timezone.get_current_timezone()).strftime("%Y-%m-%d")
                lignes.append(
                    f"- {u.nom} {u.prenom} <{u.courriel}> | "
                    f"Affiliation: {aff} | Labo: {labo} | Activation: {date_act}"
                )

            corps_admin = (
                f"{len(desactives)} compte(s) desactive(s) faute de reponse a la re-verification :\n\n"
                + "\n".join(lignes)
                + "\n\n"
                "Ces comptes peuvent etre reactives manuellement dans l'admin si necessaire.\n"
                "Les usagers concernes ont ete prevus de contacter l'administrateur s'ils "
                "souhaitent reactiver leur compte."
            )
            send_mail(
                subject=f"[Plateforme cellulaire] {len(desactives)} compte(s) desactive(s) automatiquement",
                message=corps_admin,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=dests_admin,
                fail_silently=False,
            )

        self.stdout.write(self.style.SUCCESS(
            f"Termine : {len(desactives)} compte(s) desactive(s)."
        ))
