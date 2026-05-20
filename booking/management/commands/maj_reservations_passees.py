from django.core.management.base import BaseCommand
from django.utils import timezone
from booking.models import Reservation

class Command(BaseCommand):
    help = "Met à jour le statut des réservations expirées -> 'passee'"

    def handle(self, *args, **options):
        today = timezone.localdate()
        n = (Reservation.objects
             .filter(date_fin__lt=today)
             .exclude(statut__in=['passee','annulee'])
             .update(statut='passee'))
        self.stdout.write(self.style.SUCCESS(f"{n} réservation(s) mises à jour"))
