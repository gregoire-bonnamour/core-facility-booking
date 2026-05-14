# usager/management/commands/backup_db.py
import io, json, re, shutil, zipfile
from datetime import timedelta
from pathlib import Path
from django.conf import settings
from django.core.management import BaseCommand, call_command, CommandError
from django.utils import timezone
from django.utils import timezone
from datetime import timedelta
from pathlib import Path

class Command(BaseCommand):
    help = "Sauvegarde la base SQLite + dump JSON, compresse en .zip et applique une rotation (7 daily + 8 weekly)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-rotate",
            action="store_true",
            help="Ne pas appliquer la rotation (utile pour tests)",
        )

    def handle(self, *args, **options):
        now = timezone.now()
        ts = now.strftime("%Y%m%d_%H%M%S")

        base_dir = Path(settings.BASE_DIR)
        backups_dir = base_dir / "backups"
        backups_dir.mkdir(parents=True, exist_ok=True)

        # 1) chemins sources
        db_path = Path(settings.DATABASES["default"]["NAME"]).resolve()
        if not db_path.exists():
            raise CommandError(f"Base SQLite introuvable: {db_path}")

        # 2) fichiers temporaires à inclure dans le zip
        tmp_dir = backups_dir / f"tmp_{ts}"
        tmp_dir.mkdir(parents=True, exist_ok=True)

        # 2.a) copie physique de la SQLite
        db_copy = tmp_dir / "db.sqlite3"
        shutil.copy2(db_path, db_copy)

        # 2.b) dump JSON
        dump_path = tmp_dir / "dump.json"
        with dump_path.open("w", encoding="utf-8") as f:
            call_command("dumpdata", "--natural-foreign", "--natural-primary", stdout=f)

        # 3) créer l’archive
        zip_name = backups_dir / f"reservation_backup_{ts}.zip"
        with zipfile.ZipFile(zip_name, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            z.write(db_copy, arcname="db.sqlite3")
            z.write(dump_path, arcname="dump.json")

            # petit manifest
            manifest = {
                "created_at": now.isoformat(),
                "django_settings": settings.SETTINGS_MODULE,
                "db_file": str(db_path),
                "site_url": getattr(settings, "SITE_URL", ""),
                "timezone": str(getattr(settings, "TIME_ZONE", "")),
            }
            z.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))

        # nettoyage du tmp
        shutil.rmtree(tmp_dir, ignore_errors=True)

        self.stdout.write(self.style.SUCCESS(f"✅ Backup créé: {zip_name.name}"))

        # 4) rotation (sauf si --no-rotate)
        if not options["no_rotate"]:
            removed = self._apply_rotation(backups_dir)
            if removed:
                self.stdout.write(self.style.WARNING(f"🧹 Rotation: supprimé {len(removed)} ancien(s) backup:"))
                for p in removed:
                    self.stdout.write(f"   - {p.name}")
            else:
                self.stdout.write("🧹 Rotation: rien à supprimer.")

    # ---------- Rotation policy: 7 daily + 8 weekly ----------
    def _apply_rotation(self, backups_dir: Path):
        """
        Conserve:
          - 1 backup par jour pour les 7 derniers jours (aujourd’hui inclus)
          - 1 backup par semaine ISO pour les 8 semaines précédentes
        Supprime le reste.
        """
        pattern = re.compile(r"^reservation_backup_(\d{8})_(\d{6})\.zip$")
        backups = []
        for p in backups_dir.glob("reservation_backup_*.zip"):
            m = pattern.match(p.name)
            if not m:
                continue
            date_str, time_str = m.groups()
            dt = timezone.datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
            if settings.USE_TZ:
                dt = timezone.make_aware(dt, timezone.get_current_timezone())
            backups.append((p, dt))

        if not backups:
            return []

        backups.sort(key=lambda x: x[1], reverse=True)

        now = timezone.now()
        tz = timezone.get_current_timezone() if settings.USE_TZ else None

        # Fenêtres de conservation
        daily_cutoff = (now - timedelta(days=6)).date()  # conserve un par jour pour J-0..J-6

        keep_weeks = set()
        for i in range(1, 9):  # 8 semaines précédentes
            d = (now - timedelta(weeks=i)).date()
            iso_year, iso_week, _ = d.isocalendar()
            keep_weeks.add((iso_year, iso_week))

        kept = set()          # <-- manquait
        kept_by_day = {}      # date -> Path
        kept_by_week = {}     # (iso_year, iso_week) -> Path

        for p, dt in backups:
            d = dt.astimezone(tz).date() if tz else dt.date()
            # DAILY
            if d >= daily_cutoff:
                if d not in kept_by_day:
                    kept.add(p)
                    kept_by_day[d] = p
                continue

            # WEEKLY
            iso_year, iso_week, _ = d.isocalendar()
            key = (iso_year, iso_week)
            if key in keep_weeks and key not in kept_by_week:
                kept.add(p)
                kept_by_week[key] = p
                continue

        # Toujours conserver le plus récent
        most_recent = backups[0][0]
        kept.add(most_recent)

        removed = []
        for p, _ in backups:
            if p not in kept:
                try:
                    p.unlink(missing_ok=True)
                    removed.append(p)
                except Exception:
                    pass

        return removed

