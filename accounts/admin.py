# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

"""
Module : user_profile.admin
---------------------
Configuration de l’interface d’administration Django pour l’application `user_profile`.

Permet :
- la gestion des tables de référence (Role, Affiliation, Laboratory),
- la gestion complète des usagers (modèle UserProfile),
- l’utilisation d’un formulaire personnalisé (UserProfileAdminForm) pour
  améliorer la saisie des usagers dans l’admin.
"""

from django.contrib import admin
from .models import Role, Affiliation, Laboratory, UserProfile,  News, TrainingInvitation
from .forms import UserProfileAdminForm
from django.utils import timezone
from django.db.models import Q
from dateutil.relativedelta import relativedelta
from django.urls import reverse
from django.http import HttpResponseRedirect

# === Enregistrements simples ===
# On peut utiliser admin.site.register(Role) directement
admin.site.register(Role)


# === Laboratory ===
@admin.register(Laboratory)
class LaboratoryAdmin(admin.ModelAdmin):
    """
    Interface d’administration pour les laboratoires.
    Affiche et filtre par affiliation.
    """
    list_display = ('name', 'affiliation')
    list_filter = ('affiliation',)
    search_fields = ('name',)


# === Affiliation ===
@admin.register(Affiliation)
class AffiliationAdmin(admin.ModelAdmin):
    """
    Interface d’administration pour les affiliations (universités, compagnies, etc.).
    """
    list_display = ('name', 'assistance_rate')
    search_fields = ('name',)

    # + Filtre latéral : À revalider (≥5 ans)
class ARevaliderFilter(admin.SimpleListFilter):
    title = "À revalider (≥5 ans)"
    parameter_name = "a_revalider"

    def lookups(self, request, model_admin):
        return (("oui", "Oui"), ("non", "Non"))

    def queryset(self, request, qs):
        seuil = timezone.now() - relativedelta(years=5)
        q_due = Q(is_active=True) & (
            Q(last_reverification_date__isnull=True, activation_date__lte=seuil)
            | Q(last_reverification_date__lte=seuil)
        )
        if self.value() == "oui":
            return qs.filter(q_due)
        if self.value() == "non":
            return qs.exclude(q_due)
        return qs

# + Action : marquer revalidé aujourd'hui
@admin.action(description="Marquer revalidé aujourd'hui")
def marquer_revalide(modeladmin, request, queryset):
    queryset.update(last_reverification_date=timezone.now())
    


# === UserProfile ===
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    form = UserProfileAdminForm

    # Colonnes affichées
    list_display = (
        'first_name', 'name', 'email',
        'fonction', 'affiliation', 'laboratoire',
        'is_active', 'is_platform_admin',
        'activation_date', 
    )

    # Recherche
    search_fields = ('first_name', 'name', 'email', 'affiliation__nom', 'laboratoire__nom')

    # Filtres latéraux
    list_filter = ('affiliation', 'laboratoire', 'fonction', 'is_active', 'is_platform_admin', ARevaliderFilter)

    # Sélection multiple M2M
    filter_horizontal = ['authorized_equipment']

    # Champs dans le formulaire
    fields = [
        'user',
        'first_name', 'name', 'email',
        'fonction', 'affiliation', 'laboratoire',
        'authorized_equipment',
        'is_active', 'is_platform_admin',
        'activation_date', 'last_reverification_date',  # ✅ visibles/éditables
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
            return queryset.exclude(first_name="").exclude(name="")
        if self.value() == "non":
            return queryset.filter(first_name="").filter(name="")
        return queryset
        
@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ('title', 'published_at', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('title', 'content')
    
class TrainingInvitationAdmin(admin.ModelAdmin):
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
        url = reverse("admin_valider_formation")  # name défini dans urls.py
        return HttpResponseRedirect(url)


admin.site.register(TrainingInvitation, TrainingInvitationAdmin)
