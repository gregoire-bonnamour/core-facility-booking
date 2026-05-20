# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

"""
Module : usager.views
---------------------
Vues de l’application `usager` :
- inscription d’un nouvel utilisateur (User + Usager) et confirmation par email,
- invitation d’usagers (admin),
- profil de l’usager connecté,
- endpoint AJAX pour récupérer les laboratoires d’une affiliation.

Notes :
- L’authentification se fait par email (voir accounts.backends.EmailAuthBackend).
- L’inscription crée un User inactif puis envoie un lien de confirmation.
- La confirmation active le User + l’Usager.
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

from .forms import InvitationForm, InscriptionForm
from .models import Usager, Invitation, Laboratoire, News
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
import logging
logger = logging.getLogger(__name__)
from django.core.mail import EmailMessage
from django.core.mail import EmailMultiAlternatives
from .utils import est_admin_plateforme
import tempfile, os


def inscription(request):
    """
    Inscription d'un nouvel utilisateur + création du profil Usager.

    GET :
        - Affiche le formulaire d’inscription (pré-remplit email via ?courriel= si présent).

    POST :
        - Valide le formulaire `InscriptionForm` :
            * crée un User (inactif) + un Usager lié,
            * tente d’associer les équipements autorisés depuis une éventuelle Invitation,
            * génère un lien de confirmation (uidb64 + token),
            * envoie le courriel de confirmation.

        - Rend la page de confirmation d’envoi (`inscription_confirmation.html`).

    Contexte rendu :
        - form : InscriptionForm
    """
    lang = (request.GET.get("lang") or "").lower()
    tpl = "usager/inscription_en.html" if lang == "en" else "usager/inscription.html"

    if request.method == 'POST':
        form = InscriptionForm(request.POST, request=request, language=lang)
        if form.is_valid():
            # Création User (inactif) + Usager (lié)
            user = form.save()

            # Génération du lien de confirmation
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            activation_url = request.build_absolute_uri(f"/usager/confirmation/{uid}/{token}/")

            # Envoi du courriel de confirmation
            subject = "Confirmation de votre inscription"
            message = render_to_string("usager/email_confirmation.html", {
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

            return render(request, 'usager/inscription_confirmation.html', {'email': user.email})
        else:
            # Log structurée (passe par la config LOGGING des settings)
            logger.warning("Erreurs formulaire inscription: %s", form.errors)
    else:
        form = InscriptionForm(request=request, language=lang)

    return render(request, tpl, {'form': form})


def confirmer_inscription(request, uidb64, token):
    """
    Active le compte utilisateur via le lien de confirmation envoyé par email.

    - Décodage de l’UID (uidb64) pour retrouver le User.
    - Vérification du token (time-based).
    - Si valide :
        * active `user.is_active = True`,
        * si un profil Usager existe → `usager.est_actif = True`,
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
            user.usager.est_actif = True
            user.usager.save()
        messages.success(request, "Votre adresse a été confirmée. Vous pouvez maintenant vous connecter.")
        return redirect('login')  # URL de la vue de connexion
    else:
        messages.error(request, "Le lien de confirmation est invalide ou a expiré.")
        return redirect('accounts:inscription')


@user_passes_test(est_admin_plateforme)
def inviter_usager(request):
    """
    Envoie une **invitation** à un courriel externe, avec sélection d’équipements autorisés.

    GET :
        - Affiche le formulaire `InvitationForm`.
        - Liste les invitations en attente (courriels invités sans compte Usager créé).

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
                messages.success(request, f"Rappel envoyé avec succès à {invitation.courriel}.")
            except Invitation.DoesNotExist:
                messages.error(request, "L'invitation n'existe pas ou a été supprimée.")
            return redirect('accounts:inviter_usager')

        # --- CAS 3 : SUPPRIMER ---
        if action == 'supprimer':
            invitation_id = request.POST.get('invitation_id')
            Invitation.objects.filter(pk=invitation_id).delete()
            messages.success(request, "Invitation supprimée.")
            return redirect('accounts:inviter_usager')

        # --- CAS 4 : ACTIONS DE MASSE / NOUVEAU FORMAT ---
        if action == 'supprimer_masse':
            ids = request.POST.getlist('invitation_ids')
            if ids:
                count, _ = Invitation.objects.filter(id__in=ids).delete()
                messages.success(request, f"{count} invitation(s) supprimée(s).")
            else:
                messages.warning(request, "Aucune invitation sélectionnée.")
            return redirect('accounts:inviter_usager')
        
        if action and action.startswith('relancer_'):
            try:
                invitation_id = int(action.split('_')[1])
                invitation = Invitation.objects.get(pk=invitation_id)
                _envoyer_email_invitation(request, invitation, rappel=True)
                messages.success(request, f"Rappel envoyé avec succès à {invitation.courriel}.")
            except (IndexError, ValueError, Invitation.DoesNotExist):
                messages.error(request, "Erreur lors de la relance.")
            return redirect('accounts:inviter_usager')

        # --- CAS 1 : NOUVELLE INVITATION ---
        form = InvitationForm(request.POST)
        if form.is_valid():
            # Enregistre l’invitation
            form.save(commit=False)
            courriel = form.cleaned_data['courriel']
            equipements = form.cleaned_data['equipment']

            # Déduplication : on garde la plus récente
            Invitation.objects.filter(courriel__iexact=courriel).delete()
            invitation = Invitation.objects.create(courriel=courriel)
            invitation.equipements.set(equipements)
            invitation.save()

            # Envoi du courriel
            _envoyer_email_invitation(request, invitation, rappel=False)

            messages.success(request, f"Invitation envoyée à {courriel}.")
            return redirect('accounts:inviter_usager')

    else:
        form = InvitationForm()

    # --- LISTE DES INVITATIONS EN ATTENTE ---
    # On cherche les Invitations dont le courriel n'est PAS dans la table Usager
    # (i.e. les gens qui n'ont pas encore créé leur compte)
    courriels_inscrits = Usager.objects.values_list('courriel', flat=True)
    invitations_en_attente = Invitation.objects.exclude(courriel__in=courriels_inscrits).order_by('-date_envoi')

    return render(request, 'usager/inviter_usager.html', {
        'form': form,
        'invitations_en_attente': invitations_en_attente
    })


def _envoyer_email_invitation(request, invitation, rappel=False):
    """
    Fonction utilitaire pour envoyer (ou renvoyer) le courriel d'invitation.
    """
    # Lien d’inscription pré-rempli
    lien_inscription = request.build_absolute_uri(
        reverse("accounts:inscription") + "?" + urlencode({"courriel": invitation.courriel})
    )

    prefixe = "RAPPEL : " if rappel else ""
    sujet = f"{prefixe}Invitation à utiliser la plateforme de réservation"

    intro = (
        "Bonjour,\n\n"
        "Ceci est un rappel pour votre invitation à la plateforme."
        if rappel else
        "Bonjour,\n\n"
        "Vous avez été invité à utiliser la plateforme de microscopie et cytométrie du YourFacility."
    )

    message = (
        f"{intro}\n\n"
        "Pour créer votre compte (ou finaliser votre inscription), veuillez cliquer sur le lien suivant :\n"
        f"{lien_inscription}\n\n"
        "Ceci est un courriel automatique.\n\n"
        "Cordialement,\n"
        "L’équipe de la plateforme de microscopie et cytométrie du YourFacility\n"
    )

    send_mail(
        sujet,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [invitation.courriel],
        fail_silently=False,
    )



@login_required
def profil(request):
    """
    Affiche le profil de l’utilisateur connecté.

    Contexte rendu :
        - user  : request.user (Django User)
        - usager: profil Usager lié (peut être None si non créé)
    """
    usager = getattr(request.user, 'accounts', None)
    return render(request, 'usager/profil.html', {'user': request.user, 'accounts': usager})


@require_GET
def get_laboratoires_par_affiliation(request):
    """
    Endpoint AJAX (GET) : retourne les laboratoires d’une affiliation donnée.

    Paramètres :
        - affiliation_id : identifiant d’Affiliation (GET)

    Réponse (JSON) :
        {
            "laboratoires": [
                {"id": <int>, "nom": <str>}, ...
            ]
        }
    """
    affiliation_id = request.GET.get('affiliation_id')
    if affiliation_id:
        labos = Laboratoire.objects.filter(affiliation_id=affiliation_id).order_by('nom')
        data = [{'id': l.id, 'nom': l.nom} for l in labos]
        return JsonResponse({'laboratoires': data})
    return JsonResponse({'laboratoires': []})


@user_passes_test(est_admin_plateforme)
def valider_formations(request):
    invitations_qs = (Invitation.objects
                      .select_related('reservation__equipement')
                      .filter(reservation__est_formation=True, date_validation__isnull=True))

    if request.method == "POST":
        action = request.POST.get("action")  # "validate" ou "delete"
        ids = request.POST.getlist("invitation_ids")

        if not ids:
            messages.warning(request, "Aucune invitation sélectionnée.")
            return redirect(request.path)

        # 1) SUPPRIMER LA SÉLECTION
        if action == "delete":
            deleted, _ = Invitation.objects.filter(id__in=ids, date_validation__isnull=True).delete()
            if deleted:
                messages.success(request, f"{deleted} invitation(s) supprimée(s).")
            else:
                messages.info(request, "Aucune invitation supprimée (déjà validée ?).")
            return redirect(request.path)

        # 2) VALIDER LA SÉLECTION
        ok, skip, errors = 0, 0, []
        for inv in invitations_qs.filter(id__in=ids):
            courriel = inv.courriel
            resa = inv.reservation
            equipement = resa.equipement if resa else None
            usager = Usager.objects.filter(courriel__iexact=courriel).first()

            if not usager or not equipement:
                skip += 1
                errors.append(f"{courriel} (usager inexistant ou réservation manquante)")
                continue

            usager.equipements_autorises.add(equipement)
            inv.date_validation = timezone.now()
            inv.save(update_fields=["date_validation"])
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
        courriel = inv.courriel
        user_exists = User.objects.filter(email__iexact=courriel).exists()
        usager_exists = Usager.objects.filter(courriel__iexact=courriel).exists()
        etat = "✅ Inscrit" if user_exists and usager_exists else "❌ Non inscrit"
        equipement = inv.reservation.equipement.nom if inv.reservation else "—"
        date_formation = inv.reservation.date_debut.strftime("%Y-%m-%d") if inv.reservation else "—"
        lignes.append({
            "id": inv.id,
            "courriel": courriel,
            "etat": etat,
            "equipement": equipement,
            "date_formation": date_formation,
        })

    return render(request, "admin/valider_formations.html", {"invitations": lignes})


@login_required

def confirmer_activite(request, token):
    """
    Confirmation d'activite via le lien envoye par courriel (re-verification 5 ans).
    Le token est signe avec django.core.signing (max_age=30 jours).
    """
    from django.core import signing
    from django.utils import timezone

    try:
        data = signing.loads(token, max_age=30 * 86400, salt="reverification")
        usager_id = data["usager_id"]
    except signing.SignatureExpired:
        return render(request, "usager/confirmer_activite.html", {
            "statut": "expire",
        })
    except (signing.BadSignature, KeyError):
        return render(request, "usager/confirmer_activite.html", {
            "statut": "invalide",
        })

    try:
        usager = Usager.objects.get(pk=usager_id)
    except Usager.DoesNotExist:
        return render(request, "usager/confirmer_activite.html", {
            "statut": "invalide",
        })

    if not usager.est_actif:
        return render(request, "usager/confirmer_activite.html", {
            "statut": "desactive",
        })

    usager.date_derniere_reverification = timezone.now()
    usager.save(update_fields=["date_derniere_reverification"])

    return render(request, "usager/confirmer_activite.html", {
        "statut": "ok",
        "accounts": usager,
    })


def accueil(request):
    is_admin = request.user.is_staff
    equipements = request.user.equipements.all()
    nb_reservations_en_attente = 0

    if is_admin:
        from booking.models import Reservation
        nb_reservations_en_attente = Reservation.objects.filter(statut='en_attente').count()

    news_list = (News.objects
                 .filter(actif=True)
                 .only('id', 'titre', 'contenu', 'date_publication')  # optionnel
                 .order_by('-date_publication')[:5])
                 

    
    return render(request, 'usager/accueil.html', {
        'is_admin': is_admin,
        'equipment': equipements,
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
    "Réservations, retards et assistance (fenêtre de modification/suppression et facturation).",
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
    next_url = request.POST.get("next") or request.GET.get("next") or reverse("accueil")

    # — NEW: choisir le template d'affichage selon ?lang=en (FR par défaut)
    lang = (request.GET.get("lang") or "").lower()
    tpl = "usager/reglement_en.html" if lang == "en" else "usager/reglement.html"

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
            profil = Usager.objects.filter(compte_utilisateur=u).first()
            if profil:
                profil.reglement_accepte = True
                profil.reglement_accepte_at = timezone.now()
                profil.save(update_fields=["reglement_accepte", "reglement_accepte_at"])

            # 1) Générer le PDF (optionnel) — ne bloque jamais
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
                pdf_tpl = "usager/reglement_pdf_en.html" if lang == "en" else "usager/reglement_pdf.html"
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
                subject = "Règlement de la plateforme — confirmation"
                body = (
                    "Bonjour,\n\n"
                    "Votre acceptation du règlement a été enregistrée.\n"
                    + ("Une copie PDF est jointe.\n\n" if pdf_bytes else "La pièce jointe PDF n'a pas pu être générée.\n\n")
                    + ("[DEBUG] Erreur PDF: " + pdf_err + "\n\n" if settings.DEBUG and pdf_err else "")
                    + "Cordialement,\nL’équipe de la plateforme"
                )
                pdf_name = "Reglement-Plateforme.pdf"
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
                    "Règlement accepté. " + ("Un PDF vous a été envoyé par courriel." if pdf_bytes else "Courriel envoyé sans PDF.")
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

    tpl = "usager/reglement_lecture_en.html" if lang == "en" else "usager/reglement_lecture.html"

    return render(request, tpl)



def _envoyer_reglement_pdf(request):
    """
    Rend un PDF à partir d'un template (usager/reglement_pdf.html) et l'envoie à l'usager.
    """
    if not HTML:
        raise RuntimeError("WeasyPrint n'est pas disponible dans l'environnement.")

    user = request.user
    usager_email = getattr(user, "email", "") or getattr(getattr(user, "accounts", None), "courriel", "")
    if not usager_email:
        raise RuntimeError("Aucune adresse courriel n'est associée à votre compte.")

    contexte_pdf = {
        "user": user,
        "points": REGLEMENT_POINTS,
        "date": timezone.now(),
        "site_url": getattr(settings, "SITE_URL", ""),
    }
    html_string = render_to_string("usager/reglement_pdf.html", contexte_pdf)
    pdf_bytes = HTML(string=html_string, base_url=getattr(settings, "SITE_URL", "")).write_pdf()

    subject = "Règlement de la plateforme – confirmation d’acceptation"
    body = (
        "Bonjour,\n\n"
        "Vous trouverez en pièce jointe le règlement de la plateforme que vous venez d’accepter.\n"
        "Conservez ce document pour vos archives.\n\n"
        "Cordialement,\nL’équipe de la plateforme"
    )
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@example.com")

    msg = EmailMessage(subject=subject, body=body, from_email=from_email, to=[usager_email])
    msg.attach("Reglement-Plateforme.pdf", pdf_bytes, "application/pdf")
    msg.send(fail_silently=False)
    
@login_required
def reglement(request, *args, **kwargs):
    return reglement_view(request)
