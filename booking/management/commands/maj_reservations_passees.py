from django.core.management.base import BaseCommand
from django.utils import timezone
from booking.models import Reservation

class Command(BaseCommand):
    help = "Met à day_of_week le status des réservations expirées -> 'past'"

    def handle(self, *args, **options):
        today = timezone.localdate()
        n = (Reservation.objects
             .filter(end_date__lt=today)
             .exclude(status__in=['past','cancelled'])
             .update(status='past'))
        self.stdout.write(self.style.SUCCESS(f"{n} reservation(s) updated to 'past'"))
