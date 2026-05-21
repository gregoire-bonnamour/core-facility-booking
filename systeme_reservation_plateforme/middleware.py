# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NoCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

# systeme_reservation_plateforme/middleware.py
from django.shortcuts import redirect
from urllib.parse import quote
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin

EXEMPT_PREFIXES = (
    '/static/',           # fichiers statiques
    '/admin/',            # admin (login, logout, etc.)
    '/user_profile/inscription',  # page d'inscription publique
    '/user_profile/confirmation', # lien email de confirmation
)

def _is_exempt_path(path: str) -> bool:
    return any(path.startswith(p) for p in EXEMPT_PREFIXES)

SAFE_PREFIXES = (
    "/static/",
    "/media/",
    "/admin/login",
    "/user_profile/reglement",
    "/accounts/login",
    "/accounts/logout",
)

SAFE_NAMES = {
    "accounts:reglement",
    "logout",
    "login",
}

class ReglementAcceptanceMiddleware(MiddlewareMixin):
    def process_request(self, request):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return None  # pas connecté → ne pas bloquer

        path = request.path or ""
        # Prefixes safe
        if path.startswith(SAFE_PREFIXES):
            return None

        # Names safe
        try:
            # On résout le name si possible (ignore exceptions)
            resolver_match = request.resolver_match
            if resolver_match and resolver_match.view_name in SAFE_NAMES:
                return None
        except Exception:
            pass

        # Si déjà accepté → continuer
        profil = getattr(getattr(user, "user_profile", None), "id", None)
        # On récupère prudemment via reverse relation si ton modèle s'appelle UserProfile
        try:
            user_profile = getattr(user, "user_profile", None)
            if user_profile and getattr(user_profile, "terms_accepted", False):
                return None
        except Exception:
            return None  # en cas d'incertitude, on ne bloque pas

        # Sinon → redirige vers la page règlement (avec next)
        reglement_url = reverse("accounts:reglement")
        if path != reglement_url:
            return redirect(f"{reglement_url}?next={quote(path)}")

        return None