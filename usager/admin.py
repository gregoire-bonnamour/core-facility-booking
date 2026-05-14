# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

"""
Module : usager.admin
---------------------
Configuration de l’interface d’administration Django pour l’application `usager`.

Permet :
- la gestion des tables de référence (Fonction, Affiliation, Laboratoire),
- la gestion complète des usagers (modèle Usager),
- l’utilisation d’un formulaire personnalisé (UsagerAdminForm) pour
  améliorer la saisie des usagers dans l’admin.
"""

from django.contrib import admin
from .models import Fonction, Affiliation, Laboratoire, Usager,  News, InvitationFormation
from .forms import UsagerAdminForm
from django.utils import timezone
from django.db.models import Q
from dateutil.relativedelta import relativedelta
from django.urls import reverse
from django.http import HttpResponseRedirect

# === Enregistrements simples ===
# On peut utiliser admin.site.register(Fonction) directement
admin.site.register(Fonction)


# === Laboratoire ===
@admin.register(Laboratoire)
class LaboratoireAdmin(admin.ModelAdmin):
    """
    Interface d’administration pour les laboratoires.
    Affiche et filtre par affiliation.
    """
    list_display = ('nom', 'affiliation')
    list_filter = ('affiliation',)
    search_fields = ('nom',)


# === Affiliation ===
@admin.register(Affiliation)
class AffiliationAdmin(admin.ModelAdmin):
    """
    Interface d’administration pour les affiliations (universités, compagnies, etc.).
    """
    list_display = ('nom', 'tarif_assistance')
    search_fields = ('nom',)

    # + Filtre latéral : À revalider (≥5 ans)
class ARevaliderFilter(admin.SimpleListFilter):
    title = "À revalider (≥5 ans)"
    parameter_name = "a_revalider"

    def lookups(self, request, model_admin):
        return (("oui", "Oui"), ("non", "Non"))

    def queryset(self, request, qs):
        seuil = timezone.now() - relativedelta(years=5)
        q_due = Q(est_actif=True) & (
            Q(date_derniere_reverification__isnull=True, date_activation__lte=seuil)
            | Q(date_derniere_reverification__lte=seuil)
        )
        if self.value() == "oui":
            return qs.filter(q_due)
        if self.value() == "non":
            return qs.exclude(q_due)
        return qs

# + Action : marquer revalidé aujourd'hui
@admin.action(description="Marquer revalidé aujourd'hui")
def marquer_revalide(modeladmin, request, queryset):
    queryset.update(date_derniere_reverification=timezone.now())
    


# === Usager ===
@admin.register(Usager)
class UsagerAdmin(admin.ModelAdmin):
    form = UsagerAdminForm

    # Colonnes affichées
    list_display = (
        'prenom', 'nom', 'courriel',
        'fonction', 'affiliation', 'laboratoire',
        'est_actif', 'est_admin',
        'date_activation', 
    )

    # Recherche
    search_fields = ('prenom', 'nom', 'courriel', 'affiliation__nom', 'laboratoire__nom')

    # Filtres latéraux
    list_filter = ('affiliation', 'laboratoire', 'fonction', 'est_actif', 'est_admin', ARevaliderFilter)

    # Sélection multiple M2M
    filter_horizontal = ['equipements_autorises']

    # Champs dans le formulaire
    fields = [
        'compte_utilisateur',
        'prenom', 'nom', 'courriel',
        'fonction', 'affiliation', 'laboratoire',
        'equipements_autorises',
        'est_actif', 'est_admin',
        'date_activation', 'date_derniere_reverification',  # ✅ visibles/éditables
    ]

    # Actions en masse
    actions = [marquer_revalide]

    @admin.display(boolean=True, description="À revalider (≥5 ans)")
    def flag_a_revalider(self, obj):
        return obj.doit_reverification


class ProfilCompletFilter(admin.SimpleListFilter):
    title = "Profil complété"
    parameter_name = "profil_complet"

    def lookups(self, request, model_admin):
        return (
            ("oui", "Oui"),
            ("non", "Non"),
        )

    def queryset(self, request, queryset):
        if self.value() == "oui":
            return queryset.exclude(prenom="").exclude(nom="")
        if self.value() == "non":
            return queryset.filter(prenom="").filter(nom="")
        return queryset
        
@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ('titre', 'date_publication', 'actif')
    list_filter = ('actif',)
    search_fields = ('titre', 'contenu')
    
class InvitationFormationAdmin(admin.ModelAdmin):
    """
    Proxy utilisé uniquement pour afficher une entrée
    'Validation des formations' dans le menu admin.
    Quand on clique dessus, on est redirigé vers la vue
    usager_views.valider_formations.
    """

    # On interdit toute action CRUD classique
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    # Au clic sur le lien dans le menu, on redirige vers la vue custom
    def changelist_view(self, request, extra_context=None):
        url = reverse("admin_valider_formation")  # nom défini dans urls.py
        return HttpResponseRedirect(url)


admin.site.register(InvitationFormation, InvitationFormationAdmin)
