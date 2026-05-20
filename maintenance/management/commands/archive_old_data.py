from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

# from booking.models import Reservation  # décommente et adapte quand prêt

class Command(BaseCommand):
    help = "Exemple: archiver/supprimer des données anciennes (à adapter avant usage)."

    def add_arguments(self, parser):
        parser.add_argument("--months", type=int, default=24, help="Âge en mois à partir duquel on nettoie.")

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Ne fait rien, affiche seulement ce qui serait fait.",
        )

    def handle(self, *args, **opts):
        months = opts["months"]
        dry = opts["dry_run"]

        cutoff = timezone.now() - timedelta(days=months*30)

        # Exemple d’idée (à adapter à ton modèle):
        # qs = Reservation.objects.filter(date_fin__lt=cutoff)
        # count = qs.count()
        count = 0  # placeholder

        if dry:
            self.stdout.write(self.style.WARNING(f"[DRY-RUN] {count} éléments seraient archivés/supprimés (< {cutoff.date()})."))
            return

        # Exemple:
        # qs.delete()
        self.stdout.write(self.style.SUCCESS(f"Nettoyage terminé. {count} éléments traités."))
