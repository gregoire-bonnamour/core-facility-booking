# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

"""
Commande Django : emails_equipement
------------------------------------
Génère la liste des courriels des usagers autorisés pour un équipement donné.

Usage:
    python manage.py emails_equipement "Nom de l'équipement"
    python manage.py emails_equipement "Microscope" --actifs-seulement=False
    python manage.py emails_equipement "Cytomètre" --format email
    python manage.py emails_equipement "Microscope" --format csv
"""

from django.core.management.base import BaseCommand, CommandError
from equipements.models import Equipement
from usager.models import Usager


class Command(BaseCommand):
    help = "Génère la liste des courriels des usagers autorisés pour un équipement"

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
        equipements = Equipement.objects.filter(nom__icontains=equipement_nom)

        if not equipements.exists():
            raise CommandError(
                f"Aucun équipement trouvé avec le nom '{equipement_nom}'. "
                f"Vérifiez l'orthographe ou utilisez une recherche partielle."
            )

        if equipements.count() > 1:
            self.stdout.write(
                self.style.WARNING(
                    f"\nPlusieurs équipements trouvés ({equipements.count()}):"
                )
            )
            for eq in equipements:
                self.stdout.write(f"  - {eq.nom}")
            self.stdout.write(
                self.style.WARNING(
                    "\nVeuillez préciser le nom exact. Utilisation du premier résultat pour cette fois.\n"
                )
            )

        equipement = equipements.first()
        self.stdout.write(
            self.style.SUCCESS(f"\n📋 Équipement: {equipement.nom}")
        )

        # Récupération des usagers autorisés
        usagers = equipement.usagers_autorises.all()

        if actifs_seulement:
            usagers = usagers.filter(est_actif=True)

        # Comptage
        total = usagers.count()
        if total == 0:
            self.stdout.write(
                self.style.WARNING(
                    f"\n⚠️  Aucun usager {'actif ' if actifs_seulement else ''}autorisé pour cet équipement.\n"
                )
            )
            return

        # Affichage selon le format
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ {total} usager{'s' if total > 1 else ''} "
                f"{'actif' if actifs_seulement else 'trouvé'}{'s' if total > 1 else ''}\n"
            )
        )

        if format_sortie == 'liste':
            self._afficher_liste(usagers)
        elif format_sortie == 'csv':
            self._afficher_csv(usagers)
        elif format_sortie == 'email':
            self._afficher_email(usagers)

    def _afficher_liste(self, usagers):
        """Affiche une liste simple, un courriel par ligne"""
        self.stdout.write("\n📧 Liste des courriels:\n")
        for usager in usagers:
            self.stdout.write(usager.courriel)
        self.stdout.write("")  # Ligne vide à la fin

    def _afficher_csv(self, usagers):
        """Affiche un CSV avec détails (nom, prénom, courriel, statut)"""
        self.stdout.write("\n📊 Format CSV:\n")
        self.stdout.write("Nom,Prénom,Courriel,Actif,Affiliation,Laboratoire")
        for usager in usagers:
            affiliation = usager.affiliation.nom if usager.affiliation else "N/A"
            laboratoire = usager.laboratoire.nom if usager.laboratoire else "N/A"
            self.stdout.write(
                f"{usager.nom},{usager.prenom},{usager.courriel},"
                f"{'Oui' if usager.est_actif else 'Non'},{affiliation},{laboratoire}"
            )
        self.stdout.write("")  # Ligne vide à la fin

    def _afficher_email(self, usagers):
        """Affiche les courriels séparés par point-virgule pour copier-coller dans un client email"""
        courriels = "; ".join([usager.courriel for usager in usagers])
        self.stdout.write("\n✉️  Format email (copier-coller):\n")
        self.stdout.write(courriels)
        self.stdout.write("")  # Ligne vide à la fin
