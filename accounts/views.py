# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NoCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

"""
Module: user_profile.views
---------------------
Vues de l’application `user_profile` :
- inscription d’un nouvel utilisateur (User + UserProfile) et confirmation par email,
- invitation d’user_profiles (admin),
- profil de l’user_profile connecté,
- endpoint AJAX pour récupérer les laboratories d’une affiliation.

Notes:
- L’authentification se fait par email (voir accounts.backends.EmailAuthBackend).
- L’inscription crée un User inactif puis envoie un lien de confirmation.
- La confirmation active le User + l’UserProfile.
"""


from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import user_passes_test, login_required
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.utils.timezone import now
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.views.decorators.http import require_GET
from django.http import JsonResponse
from urllib.parse import urlencode

from .forms import InvitationForm, RegistrationForm
from .models import UserProfile, Invitation, Laboratory, News
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
import logging
logger = logging.getLogger(__name__)
from django.core.mail import EmailMessage
from django.core.mail import EmailMultiAlternatives
from .utils import is_platform_admin_plateforme
import tempfile, os


def inscription(request):
    """
    Inscription d'un nouvel utilisateur + création du profil UserProfile.

    GET :
        - Affiche le formulaire d’inscription (pré-remplit email via ?email= si présent).

    POST :
        - Valide le formulaire `RegistrationForm` :
            * crée un User (inactif) + un UserProfile lié,
            * tente d’associer les équipements autorisés depuis une éventuelle Invitation,
            * génère un lien de confirmation (uidb64 + token),
            * envoie le email de confirmation.

        - Rend la page de confirmation d’envoi (`inscription_confirmation.html`).

    Contexte rendu :
        - form : RegistrationForm
    """
    lang = (request.GET.get("lang") or "").lower()
    tpl = "accounts/inscription_en.html" if lang == "en" else "accounts/inscription.html"

    if request.method == 'POST':
        form = RegistrationForm(request.POST, request=request, language=lang)
        if form.is_valid():
            # Création User (inactif) + UserProfile (lié)
            user = form.save()

            # Génération du lien de confirmation
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            activation_url = request.build_absolute_uri(f"/accounts/confirmation/{uid}/{token}/")

            # Envoi du email de confirmation
            subject = "Confirmation de votre inscription"
            message = render_to_string("accounts/email_confirmation.html", {
                'user': user,
                'activation_url': activation_url,
            })
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )

            return render(request, 'accounts/inscription_confirmation.html', {'email': user.email})
        else:
            # Log structurée (passe par la config LOGGING des settings)
            logger.warning("Erreurs formulaire inscription: %s", form.errors)
    else:
        form = RegistrationForm(request=request, language=lang)

    return render(request, tpl, {'form': form})


def confirmer_inscription(request, uidb64, token):
    """
    Active le compte utilisateur via le lien de confirmation envoyé par email.

    - Décodage de l’UID (uidb64) pour retrouver le User.
    - Vérification du token (time-based).
    - Si valide :
        * active `user.is_active = True`,
        * si un profil UserProfile existe → `user_profile.is_active = True`,
        * redirige vers la page de login avec un message succès.
      Sinon :
        * message d’erreur + redirection vers l’inscription.
    """
    UserModel = get_user_model()
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = UserModel.objects.get(pk=uid)
    except (UserModel.DoesNotExist, ValueError, TypeError, OverflowError):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        if hasattr(user, "accounts"):
            user.user_profile.is_active = True
            user.user_profile.save()
        messages.success(request, "Votre adresse a été confirmée. Vous pouvez maintenant vous connecter.")
        return redirect('login')  # URL de la vue de connexion
    else:
        messages.error(request, "Le lien de confirmation est invalide ou a expiré.")
        return redirect('accounts:inscription')


@user_passes_test(is_platform_admin_plateforme)
def inviter_usager(request):
    """
    Envoie une **invitation** à un email externe, avec sélection d’équipements autorisés.

    GET :
        - Affiche le formulaire `InvitationForm`.
        - Liste les invitations en attente (emails invités sans compte UserProfile créé).

    POST :
        - Cas 1 (Formulaire) : Crée une nouvelle invitation.
        - Cas 2 (Action 'relancer') : Renvoie l'email d'invitation à un utilisateur existant.
    """
    if request.method == 'POST':
        action = request.POST.get('action')

        # --- CAS 2 : RELANCER ---
        if action == 'relancer':
            invitation_id = request.POST.get('invitation_id')
            try:
                invitation = Invitation.objects.get(pk=invitation_id)
                _envoyer_email_invitation(request, invitation, rappel=True)
                messages.success(request, f"Reminder sent successfully to {invitation.email}.")
            except Invitation.DoesNotExist:
                messages.error(request, "The invitation does not exist or has been deleted.")
            return redirect('accounts:invite_user')

        # --- CAS 3 : SUPPRIMER ---
        if action == 'supprimer':
            invitation_id = request.POST.get('invitation_id')
            Invitation.objects.filter(pk=invitation_id).delete()
            messages.success(request, "Invitation deleted.")
            return redirect('accounts:invite_user')

        # --- CAS 4 : ACTIONS DE MASSE / NOUVEAU FORMAT ---
        if action == 'supprimer_masse':
            ids = request.POST.getlist('invitation_ids')
            if ids:
                count, _ = Invitation.objects.filter(id__in=ids).delete()
                messages.success(request, f"{count} invitation(s) deleted.")
            else:
                messages.warning(request, "No invitation selected.")
            return redirect('accounts:invite_user')
        
        if action and action.startswith('relancer_'):
            try:
                invitation_id = int(action.split('_')[1])
                invitation = Invitation.objects.get(pk=invitation_id)
                _envoyer_email_invitation(request, invitation, rappel=True)
                messages.success(request, f"Reminder sent successfully to {invitation.email}.")
            except (IndexError, ValueError, Invitation.DoesNotExist):
                messages.error(request, "Erreur lors de la relance.")
            return redirect('accounts:invite_user')

        # --- CAS 1 : NOUVELLE INVITATION ---
        form = InvitationForm(request.POST)
        if form.is_valid():
            # Enregistre l’invitation
            form.save(commit=False)
            email = form.cleaned_data['email']
            equipment_set = form.cleaned_data['equipment']

            # Déduplication : on garde la plus récente
            Invitation.objects.filter(email__iexact=email).delete()
            invitation = Invitation.objects.create(email=email)
            invitation.equipment_set.set(equipment_set)
            invitation.save()

            # Envoi du email
            _envoyer_email_invitation(request, invitation, rappel=False)

            messages.success(request, f"Invitation sent to {email}.")
            return redirect('accounts:invite_user')

    else:
        form = InvitationForm()

    # --- LISTE DES INVITATIONS EN ATTENTE ---
    # On cherche les Invitations dont le email n'est PAS dans la table UserProfile
    # (i.e. les gens qui n'ont pas encore créé leur compte)
    emails_inscrits = UserProfile.objects.values_list('email', flat=True)
    invitations_en_attente = Invitation.objects.exclude(email__in=emails_inscrits).order_by('-sent_at')

    return render(request, 'accounts/inviter_usager.html', {
        'form': form,
        'invitations_en_attente': invitations_en_attente
    })


def _envoyer_email_invitation(request, invitation, rappel=False):
    """
    Role utilitaire pour envoyer (ou renvoyer) le email d'invitation.
    """
    # Lien d’inscription pré-rempli
    lien_inscription = request.build_absolute_uri(
        reverse("accounts:inscription") + "?" + urlencode({"email": invitation.email})
    )

    prefixe = "REMINDER: " if rappel else ""
    sujet = f"{prefixe}Invitation to use the core facility booking platform"

    intro = (
        "Hello,\n\n"
        "This is a reminder for your invitation to the platform."
        if rappel else
        "Hello,\n\n"
        "You have been invited to use the YourFacility Core Facility booking platform."
    )

    message = (
        f"{intro}\n\n"
        "To create your account (or complete your registration), please click the following link:\n"
        f"{lien_inscription}\n\n"
        "This is an automated email.\n\n"
        "Best regards,\n"
        "The YourFacility Core Facility Team\n"
    )

    send_mail(
        sujet,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [invitation.email],
        fail_silently=False,
    )



@login_required
def profil(request):
    """
    Affiche le profil de l’utilisateur connecté.

    Contexte rendu :
        - user  : request.user (Django User)
        - user_profile: profil UserProfile lié (peut être None si non créé)
    """
    user_profile = getattr(request.user, 'user_profile', None)
    return render(request, 'accounts/profil.html', {'user': request.user, 'accounts': user_profile})


@require_GET
def get_laboratoires_par_affiliation(request):
    """
    Endpoint AJAX (GET) : retourne les laboratories d’une affiliation donnée.

    Parameters:
        - affiliation_id : identifiant d’Affiliation (GET)

    Réponse (JSON) :
        {
            "laboratories": [
                {"id": <int>, "name": <str>}, ...
            ]
        }
    """
    affiliation_id = request.GET.get('affiliation_id')
    if affiliation_id:
        labos = Laboratory.objects.filter(affiliation_id=affiliation_id).order_by('name')
        data = [{'id': l.id, 'name': l.name} for l in labos]
        return JsonResponse({'laboratories': data})
    return JsonResponse({'laboratories': []})


@user_passes_test(is_platform_admin_plateforme)
def valider_formations(request):
    invitations_qs = (Invitation.objects
                      .select_related('reservation__equipement')
                      .filter(reservation__is_training=True, validated_at__isnull=True))

    if request.method == "POST":
        action = request.POST.get("action")  # "validate" ou "delete"
        ids = request.POST.getlist("invitation_ids")

        if not ids:
            messages.warning(request, "No invitation selected.")
            return redirect(request.path)

        # 1) SUPPRIMER LA SÉLECTION
        if action == "delete":
            deleted, _ = Invitation.objects.filter(id__in=ids, validated_at__isnull=True).delete()
            if deleted:
                messages.success(request, f"{deleted} invitation(s) supprimée(s).")
            else:
                messages.info(request, "None invitation supprimée (déjà validée ?).")
            return redirect(request.path)

        # 2) VALIDER LA SÉLECTION
        ok, skip, errors = 0, 0, []
        for inv in invitations_qs.filter(id__in=ids):
            email = inv.email
            resa = inv.reservation
            equipment = resa.equipment if resa else None
            user_profile = UserProfile.objects.filter(email__iexact=email).first()

            if not user_profile or not equipment:
                skip += 1
                errors.append(f"{email} (user profile not found or reservation missing)")
                continue

            user_profile.authorized_equipment.add(equipment)
            inv.validated_at = timezone.now()
            inv.save(update_fields=["validated_at"])
            ok += 1

        if ok:
            messages.success(request, f"{ok} formation(s) validée(s).")
        if skip:
            messages.warning(request, f"{skip} non validée(s).")
        for e in errors:
            messages.info(request, f"• {e}")

        return redirect(request.path)

    # GET : construire les lignes
    lignes = []
    for inv in invitations_qs:
        email = inv.email
        user_exists = User.objects.filter(email__iexact=email).exists()
        usager_exists = UserProfile.objects.filter(email__iexact=email).exists()
        etat = "✅ Inscrit" if user_exists and usager_exists else "❌ No inscrit"
        equipment = inv.reservation.equipment.name if inv.reservation else "—"
        date_formation = inv.reservation.start_date.strftime("%Y-%m-%d") if inv.reservation else "—"
        lignes.append({
            "id": inv.id,
            "email": email,
            "etat": etat,
            "equipment": equipment,
            "date_formation": date_formation,
        })

    return render(request, "admin/valider_formations.html", {"invitations": lignes})


@login_required

def confirmer_activite(request, token):
    """
    Confirmation d'activite via le lien envoye par email (re-verification 5 ans).
    Le token est signe avec django.core.signing (max_age=30 jours).
    """
    from django.core import signing
    from django.utils import timezone

    try:
        data = signing.loads(token, max_age=30 * 86400, salt="reverification")
        usager_id = data["usager_id"]
    except signing.SignatureExpired:
        return render(request, "accounts/confirmer_activite.html", {
            "status": "expire",
        })
    except (signing.BadSignature, KeyError):
        return render(request, "accounts/confirmer_activite.html", {
            "status": "invalide",
        })

    try:
        user_profile = UserProfile.objects.get(pk=usager_id)
    except UserProfile.DoesNotExist:
        return render(request, "accounts/confirmer_activite.html", {
            "status": "invalide",
        })

    if not user_profile.is_active:
        return render(request, "accounts/confirmer_activite.html", {
            "status": "desactive",
        })

    user_profile.last_reverification_date = timezone.now()
    user_profile.save(update_fields=["last_reverification_date"])

    return render(request, "accounts/confirmer_activite.html", {
        "status": "ok",
        "user_profile": user_profile,
    })


def accueil(request):
    is_admin = request.user.is_staff
    equipment_set = request.user.equipment_set.all()
    nb_reservations_en_attente = 0

    if is_admin:
        from booking.models import Reservation
        nb_reservations_en_attente = Reservation.objects.filter(status='pending').count()

    news_list = (News.objects
                 .filter(is_active=True)
                 .only('id', 'title', 'content', 'published_at')  # optional
                 .order_by('-published_at')[:5])
                 

    
    return render(request, 'accounts/accueil.html', {
        'is_admin': is_admin,
        'equipment': equipment_set,
        'nb_reservations_en_attente': nb_reservations_en_attente,
        'news_list': news_list,
    })
    
try:
    from weasyprint import HTML
except Exception:
    HTML = None  # au cas où WeasyPrint n’est pas installé dans l’environnement

REGLEMENT_POINTS = [
    "Publications scientifiques (acknowledgment, information et co-signature).",
    "Respect et bon usage des équipements (formation, consommables, nettoyage, signalement incident).",
    "Reservations, delays and assistance (modification/deletion window and billing).",
    "Données, sécurité et confidentialité (export, politiques YourUniversity).",
    "Sanctions graduées (rappel → avertissement → suspension → retrait d’accès).",
]

@login_required
def reglement_view(request):
    """
    Affiche le règlement + traite l'acceptation.
    Validation simple : au moins `expected` cases cochées.
    Pas d'hypothèse sur les valeurs exactes envoyées (1..5, 0..4, etc.).
    """
    # Où rediriger après succès
    next_url = request.POST.get("next") or request.GET.get("next") or reverse("home")

    # — NEW: choisir le template d'affichage selon ?lang=en (FR by default)
    lang = (request.GET.get("lang") or "").lower()
    tpl = "accounts/reglement_en.html" if lang == "en" else "accounts/reglement.html"

    if request.method == "POST":
        acks = request.POST.getlist("ack")
        expected = 0
        try:
            expected = int(request.POST.get("expected", "0"))
        except ValueError:
            expected = 0

        # ✅ Accepte si on a bien au moins N cases cochées
        if len(set(acks)) >= expected > 0:
            # Marque l'acceptation côté profil
            u = request.user
            profil = UserProfile.objects.filter(user=u).first()
            if profil:
                profil.terms_accepted = True
                profil.terms_accepted_at = timezone.now()
                profil.save(update_fields=["terms_accepted", "terms_accepted_at"])

            # 1) Générer le PDF (optional) — ne bloque jamais
            pdf_bytes = None
            pdf_err = None
            try:
                import tempfile
                from weasyprint import HTML
                ctx = {
                    "user": request.user,
                    "date": timezone.localtime(),
                    "site_url": getattr(settings, "SITE_URL", ""),
                    "points": REGLEMENT_POINTS,
                }
                pdf_tpl = "accounts/reglement_pdf_en.html" if lang == "en" else "accounts/reglement_pdf.html"
                html = render_to_string(pdf_tpl, ctx)

                # IMPORTANT: base_url en file:// absolu (Windows-safe)
                base_url = settings.SITE_URL  # ex: file:///C:/.../src

                # Créer un fichier temporaire manuel (contournement Windows)
                tmp_path = os.path.join(tempfile.gettempdir(), f"reglement_{request.user.id}.pdf")
                HTML(string=html, base_url=base_url).write_pdf(tmp_path)

                with open(tmp_path, "rb") as f:
                    pdf_bytes = f.read()

                try:
                    os.remove(tmp_path)
                except Exception:
                    pass  # on ignore si Windows garde un lock
            except Exception as e:
                pdf_bytes = None
                pdf_err = f"{e.__class__.__name__}: {e}"  # utile en DEBUG

            # 2) Envoyer l'email (toujours), avec PJ si disponible
            if lang == "en":
                subject = "Platform Rules — Confirmation"
                body = (
                    "Hello,\n\n"
                    "Your acceptance of the platform rules has been recorded.\n"
                    + ("A PDF copy is attached.\n\n" if pdf_bytes else "The PDF attachment could not be generated.\n\n")
                    + ("[DEBUG] PDF error: " + pdf_err + "\n\n" if settings.DEBUG and pdf_err else "")
                    + "Regards,\nThe Core Facility Team"
                )
                pdf_name = "Platform-Rules.pdf"
            else:
                subject = "Platform Rules — confirmation"
                body = (
                    "Hello,\n\n"
                    "Your acceptance of the platform rules has been recorded.\n"
                    + ("A PDF copy is attached.\n\n" if pdf_bytes else "The PDF attachment could not be generated.\n\n")
                    + ("[DEBUG] PDF error: " + pdf_err + "\n\n" if settings.DEBUG and pdf_err else "")
                    + "Best regards,\nThe Core Facility Team"
                )
                pdf_name = "Platform-Rules.pdf"
            to_list = [request.user.email] if getattr(request.user, "email", None) else [settings.SERVER_EMAIL]

            from django.core.mail import EmailMessage
            email = EmailMessage(
                subject=subject,
                body=body,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                to=to_list,
            )
            if pdf_bytes:
                email.attach(pdf_name, pdf_bytes, "application/pdf")

            try:
                email.send(fail_silently=False)
                messages.success(
                    request,
                    "Règlement accepté. " + ("Un PDF vous a été envoyé par email." if pdf_bytes else "Courriel envoyé sans PDF.")
                )
            except Exception:
                logger.exception("WeasyPrint: génération PDF KO")
                pdf_bytes = None

            return redirect(next_url)

        # Sinon, on ré-affiche la page avec un message explicite
        messages.error(request, "Merci de cocher les 5 cases avant d’accepter.")
        return render(request, tpl, {  # <-- utilise le template FR/EN
            "points": REGLEMENT_POINTS,
            "expected": len(REGLEMENT_POINTS),
            "next": next_url,
        })

    # GET → affichage
    return render(request, tpl, {      # <-- utilise le template FR/EN
        "points": REGLEMENT_POINTS,
        "expected": len(REGLEMENT_POINTS),
        "next": next_url,
    })


@login_required
def reglement_lecture(request):
    """
    Affiche le règlement en lecture seule (FR/EN).
    """
    lang = (request.GET.get("lang") or "").lower()

    tpl = "accounts/reglement_lecture_en.html" if lang == "en" else "accounts/reglement_lecture.html"

    return render(request, tpl)



def _envoyer_reglement_pdf(request):
    """
    Rend un PDF à partir d'un template (accounts/reglement_pdf.html) et l'envoie à l'user_profile.
    """
    if not HTML:
        raise RuntimeError("WeasyPrint n'est pas disponible dans l'environnement.")

    user = request.user
    usager_email = getattr(user, "email", "") or getattr(getattr(user, "user_profile", None), "email", "")
    if not usager_email:
        raise RuntimeError("None adresse email n'est associée à votre compte.")

    contexte_pdf = {
        "user": user,
        "points": REGLEMENT_POINTS,
        "date": timezone.now(),
        "site_url": getattr(settings, "SITE_URL", ""),
    }
    html_string = render_to_string("accounts/reglement_pdf.html", contexte_pdf)
    pdf_bytes = HTML(string=html_string, base_url=getattr(settings, "SITE_URL", "")).write_pdf()

    subject = "Platform Rules – acceptance confirmation"
    body = (
        "Hello,\n\n"
        "Please find attached the platform rules you have just accepted.\n"
        "Keep this document for your records.\n\n"
        "Best regards,\nThe Core Facility Team"
    )
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@example.com")

    msg = EmailMessage(subject=subject, body=body, from_email=from_email, to=[usager_email])
    msg.attach("Reglement-Plateforme.pdf", pdf_bytes, "application/pdf")
    msg.send(fail_silently=False)
    
@login_required
def reglement(request, *args, **kwargs):
    return reglement_view(request)
