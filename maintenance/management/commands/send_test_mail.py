from pathlib import Path
import mimetypes
from django.conf import settings
from django.core.mail import EmailMessage
from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    help = "Envoie un email de test (avec option --pdf pour joindre un fichier PDF)."

    def add_arguments(self, parser):
        parser.add_argument("--to", required=True, help="Destinataire (email).")
        parser.add_argument("--subject", default="Test Calendrier — SMTP & PDF", help="Sujet.")
        parser.add_argument("--pdf", help="Chemin vers un PDF à joindre (optional).")

    def handle(self, *args, **opts):
        to_addr = opts["to"]
        subject = opts["subject"]
        pdf_path = opts.get("pdf")

        from_addr = getattr(settings, "DEFAULT_FROM_EMAIL", None) or getattr(settings, "SERVER_EMAIL", None) or "no-reply@example.com"
        backend = getattr(settings, "EMAIL_BACKEND", "unknown")

        body = (
            "Bonjour,\n\n"
            "Ceci est un message de test envoyé par la commande Django `send_test_mail`.\n"
            f"- Backend actuel: {backend}\n"
            f"- From: {from_addr}\n"
            f"- To: {to_addr}\n\n"
            "Si une pièce jointe PDF a été fournie, elle est ajoutée.\n"
            "— Plateforme cellulaire / Calendrier\n"
        )

        msg = EmailMessage(subject=subject, body=body, from_email=from_addr, to=[to_addr])

        if pdf_path:
            p = Path(pdf_path)
            if not p.is_file():
                raise CommandError(f"PDF introuvable: {p}")
            mime, _ = mimetypes.guess_type(str(p))
            if mime is None:
                mime = "application/pdf"
            msg.attach(p.name, p.read_bytes(), mime)

        sent = msg.send(fail_silently=False)
        if sent:
            self.stdout.write(self.style.SUCCESS(f"OK: message envoyé (backend={backend})"))
        else:
            raise CommandError("Échec d'envoi (send()=0)")
