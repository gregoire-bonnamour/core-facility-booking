# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NoCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

# user_profile/utils.py

from accounts.models import Invitation, UserProfile
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.conf import settings
import re
import logging

logger = logging.getLogger('booking')

def creer_invitations_pour_formation(reservation, force_resend=False):
    """
    Gère les emails pour une formation :
    - Parse les emails (virgule, point-virgule, saut de ligne).
    - Si utilisateur existe : Notification simple.
    - Si nouvel utilisateur : Invitation à créer un compte.
    - force_resend=True : envoie à tout le monde (ex: horaire modifié).
    - force_resend=False : envoie uniquement aux nouvelles adresses.
    """
    # On sépare les emails (virgules, points-virgules, sauts de ligne)
    raw_emails = reservation.trained_emails or ''
    emails_bruts = [e.strip() for e in re.split(r'[;,\n\r]+', raw_emails) if e.strip()]
    emails = []
    for e in emails_bruts:
        try:
            validate_email(e)
            emails.append(e)
        except ValidationError:
            logger.warning(f"Adresse email invalide ignorée dans la formation {reservation.pk} : {e!r}")

    # Adresses déjà connues avant cette sauvegarde
    existing_emails = set(
        Invitation.objects.filter(reservation=reservation)
        .values_list('email', flat=True)
    )

    # Supprimer les invitations des adresses retirées de la liste
    Invitation.objects.filter(reservation=reservation).exclude(
        email__in=emails
    ).delete()

    for email in emails:
        is_new = email.lower() not in {e.lower() for e in existing_emails}

        # Mettre à day_of_week l'objet invitation
        Invitation.objects.filter(email__iexact=email, reservation=reservation).delete()
        invitation = Invitation.objects.create(
            reservation=reservation,
            email=email,
        )

        if not (is_new or force_resend):
            continue

        # 1. Vérifier si l'utilisateur existe déjà pour choisir le type de email
        user_exists = User.objects.filter(email__iexact=email).exists()
        usager_exists = UserProfile.objects.filter(email__iexact=email).exists()

        if user_exists or usager_exists:
            # CAS 1 : Utilisateur existant -> Notification d'inscription
            # ✅ fail_silently=False pour détecter les problèmes SMTP
            logger.info(f"Tentative d'envoi notification (CAS 1) à {email}")
            send_mail(
                subject=f"[Core Facility] Training Confirmation – {reservation.equipment.name}",
                message=(
                    f"Hello,\n\n"
                    f"You have been registered for a training session on: {reservation.equipment.name}\n"
                    f"Date: {reservation.start_date.strftime('%Y-%m-%d')} "
                    f"from {reservation.start_time.strftime('%H:%M')} to {reservation.end_time.strftime('%H:%M')}.\n\n"
                    f"You can access the platform here: {settings.SITE_URL}\n\n"
                    "Best regards,\n"
                    "The platform team"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            logger.info(f"Notification envoyée (CAS 1) avec succès à {email}")
        else:
            # CAS 2 : Nouveau -> Invitation à créer son compte
            # Lien d'inscription
            inscription_url = f"{settings.SITE_URL}/user_profile/inscription?email={email}"

            # Envoi mail invitation
            logger.info(f"Tentative d'envoi invitation (CAS 2) à {email}")
            send_mail(
                subject="Invitation to create an account – Core Facility Booking",
                message=(
                    f"Hello,\n\n"
                    f"You have been invited to attend a training session on: {reservation.equipment.name}\n"
                    f"on {reservation.start_date.strftime('%Y-%m-%d')} at the YourFacility core facility.\n\n"
                    f"To create your account, please click the following link:\n"
                    f"{inscription_url}\n\n"
                    "This is an automated email – please do not reply.\n\n"
                    "If you did not request this, you may ignore this message.\n\n"
                    "Best regards,\n"
                    "The YourFacility Core Facility Team\n"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            logger.info(f"Invitation envoyée (CAS 2) avec succès à {email}")

def is_platform_admin_plateforme(user):
    """
    Vérifie si l'utilisateur a les droits de gestion de la plateforme.
    Returns True si l'user_profile est Super-utilisateur (Django), Staff (Django) 
    OU a la case 'Est admin' cochée sur son profil plateforme.
    """
    return user.is_staff or user.is_superuser or (hasattr(user, 'user_profile') and getattr(user.user_profile, 'is_platform_admin', False))
