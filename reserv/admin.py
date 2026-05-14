# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

"""
Module : reserv.admin
---------------------
Configuration de l’interface d’administration pour les réservations.

Fonctionnalités :
- Affichage et filtrage des réservations dans l’admin.
- Actions personnalisées pour accepter ou refuser les demandes
  de réservations exceptionnelles.
- Envoi automatique d’un courriel à l’usager lors de l’acceptation/refus.
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
            ('oui', 'Oui (Avec durée)'),
            ('non', 'Non'),
            ('erreur', '⚠️ Oui (Durée manquante)'),
        )

    def queryset(self, request, queryset):
        from django.db.models import Q
        if self.value() == 'oui':
            return queryset.filter(assistance=True, duree_assistance_minutes__gt=0)
        
        if self.value() == 'non':
            return queryset.filter(assistance=False)
            
        if self.value() == 'erreur':
            return queryset.filter(assistance=True).filter(Q(duree_assistance_minutes__isnull=True) | Q(duree_assistance_minutes=0))
            
        return queryset

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    """
    Configuration de l’affichage des réservations dans l’admin.

    Options :
        - list_display : colonnes affichées dans la liste
        - list_filter  : filtres disponibles sur le côté
        - actions      : actions groupées (accepter/refuser)
    """
    list_display = ('usager', 'equipement', 'date_debut', 'date_fin', 'affichage_statut')
    list_filter = ('statut', 'usager', 'equipement', 'usager__affiliation', AssistanceFilter)
    search_fields = ("usager__prenom", "usager__nom", "usager__courriel")  # barre de recherche
    actions = ['accepter_reservations', 'refuser_reservations']
    #autocomplete_fields = ["usager", "equipement"]
    
    # 👇 Force the logical order in the edit/view form
    fieldsets = (
        ("Infos", {
            "fields": (("equipement", "usager"),)
        }),
        ("Période", {
            "fields": (("date_debut", "heure_debut"),
                       ("date_fin", "heure_fin")),
        }),
        ("Options", {
            "fields": ("demande_exception", "justification",
                       "est_formation", "courriels_formes",
                       "assistance", "duree_assistance_minutes",
                       "statut"),
        }),
    )
    
    def affichage_statut(self, obj):
        """
        Retourne le libellé lisible du statut (via get_statut_display()).
        """
        return obj.get_statut_display()
    affichage_statut.short_description = 'Statut'

    # ⬇️ Respecter la valeur choisie en admin, sans renvoyer les courriels de formation
    def save_model(self, request, obj, form, change):
        obj.save(force_statut=True, skip_invitations=True)

    @admin.action(description="🚫 Marquer 'annulée' (sans recalcul)")
    def annuler_reservations(self, request, queryset):
        ids = list(queryset.values_list('pk', flat=True))
        updated = Reservation.objects.filter(pk__in=ids).exclude(statut='annulee').update(statut='annulee')
        self.message_user(request, f"{updated} réservation(s) marquée(s) comme annulée(s).")

    @admin.action(description="✅ Accepter les demandes d'exception sélectionnées")
    def accepter_reservations(self, request, queryset):
        """
        Action admin pour accepter des réservations en attente :
        - Met à jour le statut → 'a_venir'
        - Sauvegarde la réservation
        - Envoie un courriel à l’usager pour confirmation
        """

       	accepted = 0

        for reservation in queryset.filter(statut='en_attente'):
            reservation.demande_exception = False
            reservation.save()

            # Notification par email
            email = reservation.usager.compte_utilisateur.email
            send_mail(
                subject="Votre réservation a été acceptée",
                message=(
                    f"Bonjour,\n\nVotre demande de réservation exceptionnelle pour "
                    f"{reservation.equipement.nom} le {reservation.date_debut} "
                    f"de {reservation.heure_debut} à {reservation.heure_fin} a été acceptée.\n\n"
                    f"Cordialement,\nL’équipe de la plateforme"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=True,
            )

        self.message_user(request, "Les réservations ont été acceptées avec succès.")

    @admin.action(description="❌ Refuser et supprimer les demandes d'exception sélectionnées")
    def refuser_reservations(self, request, queryset):
        """
        Action admin pour refuser et supprimer des réservations en attente :
        - Envoie un courriel de refus à l’usager
        - Supprime la réservation de la base
        """
        refus = queryset.filter(statut='en_attente')
        count = refus.count()

        for reservation in refus:
            # Notification par email (avant suppression)
            email = reservation.usager.compte_utilisateur.email
            send_mail(
                subject="Votre réservation a été refusée",
                message=(
                    f"Bonjour,\n\nVotre demande de réservation exceptionnelle pour "
                    f"{reservation.equipement.nom} le {reservation.date_debut} "
                    f"de {reservation.heure_debut} à {reservation.heure_fin} a été refusée.\n\n"
                    f"Cordialement,\nL’équipe de la plateforme"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=True,
            )

            reservation.delete()

        self.message_user(request, f"{count} réservation(s) ont été refusée(s) et supprimée(s).")

