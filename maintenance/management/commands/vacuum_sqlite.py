from django.core.management.base import BaseCommand
from django.conf import settings
import sqlite3
from pathlib import Path

class Command(BaseCommand):
    help = "Exécute VACUUM sur la base SQLite (récupère l'espace disque)."

    def handle(self, *args, **opts):
        db_settings = settings.DATABASES.get("default", {})
        engine = db_settings.get("ENGINE", "")
        if "sqlite" not in engine:
            self.stderr.write(self.style.ERROR("Cette commande est prévue pour SQLite."))
            return

        db_path = Path(db_settings.get("NAME"))
        if not db_path.exists():
            self.stderr.write(self.style.ERROR(f"Fichier DB introuvable: {db_path}"))
            return

        con = sqlite3.connect(str(db_path))
        try:
            con.execute("VACUUM;")
            con.commit()
            self.stdout.write(self.style.SUCCESS("VACUUM exécuté avec succès."))
        finally:
            con.close()
