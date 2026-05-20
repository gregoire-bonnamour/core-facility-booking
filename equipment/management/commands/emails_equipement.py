# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

"""
Commande Django : emails_equipement
------------------------------------
Génère la liste des emails des usagers autorisés pour un équipement donné.

Usage:
    python manage.py emails_equipement "Nom de l'équipement"
    python manage.py emails_equipement "Microscope" --actifs-seulement=False
    python manage.py emails_equipement "Cytomètre" --format email
    python manage.py emails_equipement "Microscope" --format csv
"""

from django.core.management.base import BaseCommand, CommandError
from equipment.models import Equipment
from accounts.models import UserProfile


class Command(BaseCommand):
    help = "Génère la liste des emails des usagers autorisés pour un équipement"

    def add_arguments(self, parser):
        parser.add_argument(
            'equipement_nom',
            type=str,
            help="Nom de l'équipement (recherche insensible à la casse)"
        )
        parser.add_argument(
            '--actifs-seulement',
            action='store_true',
            default=True,
            help="Afficher uniquement les usagers actifs (défaut: True)"
        )
        parser.add_argument(
            '--tous',
            action='store_true',
            help="Inclure les usagers inactifs (raccourci pour --actifs-seulement=False)"
        )
        parser.add_argument(
            '--format',
            type=str,
            choices=['liste', 'csv', 'email'],
            default='liste',
            help=(
                "Format de sortie: "
                "'liste' (un par ligne), "
                "'csv' (avec détails), "
                "'email' (séparés par ; pour copier-coller)"
            )
        )

    def handle(self, *args, **options):
        equipement_nom = options['equipement_nom']
        actifs_seulement = options['actifs_seulement'] and not options['tous']
        format_sortie = options['format']

        # Recherche de l'équipement (insensible à la casse, recherche partielle)
        equipment_set = Equipment.objects.filter(nom__icontains=equipement_nom)

        if not equipment_set.exists():
            raise CommandError(
                f"Aucun équipement trouvé avec le name '{equipement_nom}'. "
                f"Vérifiez l'orthographe ou utilisez une recherche partielle."
            )

        if equipment_set.count() > 1:
            self.stdout.write(
                self.style.WARNING(
                    f"\nPlusieurs équipements trouvés ({equipment_set.count()}):"
                )
            )
            for eq in equipment_set:
                self.stdout.write(f"  - {eq.name}")
            self.stdout.write(
                self.style.WARNING(
                    "\nVeuillez préciser le name exact. Utilisation du premier résultat pour cette fois.\n"
                )
            )

        equipment = equipment_set.first()
        self.stdout.write(
            self.style.SUCCESS(f"\n📋 Équipement: {equipment.name}")
        )

        # Récupération des usagers autorisés
        usagers = equipment.usagers_autorises.all()

        if actifs_seulement:
            usagers = usagers.filter(is_active=True)

        # Comptage
        total = usagers.count()
        if total == 0:
            self.stdout.write(
                self.style.WARNING(
                    f"\n⚠️  Aucun user_profile {'is_active ' if actifs_seulement else ''}autorisé pour cet équipement.\n"
                )
            )
            return

        # Affichage selon le format
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ {total} user_profile{'s' if total > 1 else ''} "
                f"{'is_active' if actifs_seulement else 'trouvé'}{'s' if total > 1 else ''}\n"
            )
        )

        if format_sortie == 'liste':
            self._afficher_liste(usagers)
        elif format_sortie == 'csv':
            self._afficher_csv(usagers)
        elif format_sortie == 'email':
            self._afficher_email(usagers)

    def _afficher_liste(self, usagers):
        """Affiche une liste simple, un email par ligne"""
        self.stdout.write("\n📧 Liste des emails:\n")
        for user_profile in usagers:
            self.stdout.write(user_profile.email)
        self.stdout.write("")  # Ligne vide à la fin

    def _afficher_csv(self, usagers):
        """Affiche un CSV avec détails (name, prénom, email, status)"""
        self.stdout.write("\n📊 Format CSV:\n")
        self.stdout.write("Nom,Prénom,Courriel,Actif,Affiliation,Laboratory")
        for user_profile in usagers:
            affiliation = user_profile.affiliation.name if user_profile.affiliation else "N/A"
            laboratoire = user_profile.laboratoire.name if user_profile.laboratoire else "N/A"
            self.stdout.write(
                f"{user_profile.name},{user_profile.first_name},{user_profile.email},"
                f"{'Oui' if user_profile.is_active else 'Non'},{affiliation},{laboratoire}"
            )
        self.stdout.write("")  # Ligne vide à la fin

    def _afficher_email(self, usagers):
        """Affiche les emails séparés par point-virgule pour copier-coller dans un client email"""
        emails = "; ".join([user_profile.email for user_profile in usagers])
        self.stdout.write("\n✉️  Format email (copier-coller):\n")
        self.stdout.write(emails)
        self.stdout.write("")  # Ligne vide à la fin
