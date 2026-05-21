# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NoCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

"""
Module: reserv.admin
---------------------
Configuration de l’interface d’administration pour les réservations.

Functionality:
- Affichage et filtrage des réservations dans l’admin.
- Actions personnalisées pour accepter ou refuser les demandes
  de réservations exceptionnelles.
- Envoi automatique d’un email à l’user_profile lors de l’acceptation/refus.
"""

from django.contrib import admin
from .models import Reservation
from django.core.mail import send_mail
from django.conf import settings



class AssistanceFilter(admin.SimpleListFilter):
    title = 'Assistance'
    parameter_name = 'assistance_custom'

    def lookups(self, request, model_admin):
        return (
            ('oui', 'Yes (Avec durée)'),
            ('non', 'No'),
            ('erreur', '⚠️ Yes (Durée manquante)'),
        )

    def queryset(self, request, queryset):
        from django.db.models import Q
        if self.value() == 'oui':
            return queryset.filter(assistance=True, assistance_duration_minutes__gt=0)
        
        if self.value() == 'non':
            return queryset.filter(assistance=False)
            
        if self.value() == 'erreur':
            return queryset.filter(assistance=True).filter(Q(assistance_duration_minutes__isnull=True) | Q(assistance_duration_minutes=0))
            
        return queryset

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    """
    Configuration de l’affichage des réservations dans l’admin.

    Options:
        - list_display : colonnes affichées dans la liste
        - list_filter  : filtres disponibles sur le côté
        - actions      : actions groupées (accepter/refuser)
    """
    list_display = ('user_profile', 'equipment', 'start_date', 'end_date', 'display_status')
    list_filter = ('status', 'user_profile', 'equipment', 'user_profile__affiliation', AssistanceFilter)
    search_fields = ("user_profile__first_name", "user_profile__name", "user_profile__email")  # barre de recherche
    actions = ['accepter_reservations', 'refuser_reservations']
    #autocomplete_fields = ["accounts", "equipment"]
    
    # 👇 Force the logical order in the edit/view form
    fieldsets = (
        ("Infos", {
            "fields": (('equipment', 'user_profile'),)
        }),
        ("Période", {
            "fields": (("start_date", "start_time"),
                       ("end_date", "end_time")),
        }),
        ("Options", {
            "fields": ("exception_request", "justification",
                       "is_training", "trained_emails",
                       "assistance", "assistance_duration_minutes",
                       "status"),
        }),
    )
    
    def display_status(self, obj):
        """
        Returns le libellé lisible du status (via get_status_display()).
        """
        return obj.get_status_display()
    display_status.short_description = 'Statut'

    # ⬇️ Respecter la valeur choisie en admin, sans renvoyer les emails de formation
    def save_model(self, request, obj, form, change):
        obj.save(force_status=True, skip_invitations=True)

    @admin.action(description="🚫 Mark as cancelled (no recalc)")
    def annuler_reservations(self, request, queryset):
        ids = list(queryset.values_list('pk', flat=True))
        updated = Reservation.objects.filter(pk__in=ids).exclude(status='cancelled').update(status='cancelled')
        self.message_user(request, f"{updated} reservation(s) marked as cancelled.")

    @admin.action(description="✅ Accepter les demandes d'exception sélectionnées")
    def accepter_reservations(self, request, queryset):
        """
        Action admin pour accepter des réservations en attente :
        - Met à day_of_week le status → 'upcoming'
        - Sauvegarde la réservation
        - Envoie un email à l’user_profile pour confirmation
        """

       	accepted = 0

        for reservation in queryset.filter(status='pending'):
            reservation.exception_request = False
            reservation.save()

            # Email notification
            email = reservation.user_profile.user.email
            send_mail(
                subject="Your reservation has been accepted",
                message=(
                    f"Hello,\n\nYour exception reservation request for "
                    f"{reservation.equipment.name} on {reservation.start_date} "
                    f"from {reservation.start_time} to {reservation.end_time} has been accepted.\n\n"
                    "Best regards,\nThe Core Facility Team"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=True,
            )

        self.message_user(request, "Reservations have been accepted successfully.")

    @admin.action(description="❌ Refuser et supprimer les demandes d'exception sélectionnées")
    def refuser_reservations(self, request, queryset):
        """
        Action admin pour refuser et supprimer des réservations en attente :
        - Envoie un email de refus à l’user_profile
        - Supprime la réservation de la base
        """
        refus = queryset.filter(status='pending')
        count = refus.count()

        for reservation in refus:
            # Email notification (avant suppression)
            email = reservation.user_profile.user.email
            send_mail(
                subject="Your reservation has been declined",
                message=(
                    f"Hello,\n\nYour exception reservation request for "
                    f"{reservation.equipment.name} on {reservation.start_date} "
                    f"from {reservation.start_time} to {reservation.end_time} has been declined.\n\n"
                    "Best regards,\nThe Core Facility Team"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=True,
            )

            reservation.delete()

        self.message_user(request, f"{count} reservation(s) have been declined and deleted.")

