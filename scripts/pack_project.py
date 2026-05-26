# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NoCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

import os, zipfile, sys
from datetime import datetime
from pathlib import Path

# --- réglages -------------------------------------------
# Dossiers lourds à exclure (tu peux ajuster)
DIR_EXCLUDE = {
    ".venv", "venv", ".git", ".idea", ".vscode",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox",
    "node_modules", "dist", "build", "htmlcov",
    "staticfiles", "collected_static", "media",  # garde "media" exclu pour limiter la taille
    "backups", "sent_emails",  # si tu veux vérifier ces dossiers, enlève-les d'ici
}
# Fichiers à exclure par extension
EXT_EXCLUDE = {".pyc", ".pyo", ".log", ".zip"}
# Fichiers .env explicitement à inclure même s’ils matchent un pattern
ENV_INCLUDE = {".env.local", ".env.prod", ".env.prod.template"}
# --------------------------------------------------------

def find_project_root(start: Path) -> Path | None:
    # remonte jusqu’à trouver manage.py
    p = start
    for _ in range(10):
        if (p / "manage.py").exists():
            return p
        if p.parent == p:
            break
        p = p.parent
    return None

def should_exclude(path: Path, rel: Path) -> bool:
    # garde toujours les .env explicitement inclus
    if rel.name in ENV_INCLUDE:
        return False
    # exclusions par dossier
    parts = set(rel.parts)
    if parts & DIR_EXCLUDE:
        return True
    # exclusions par extension
    if path.suffix.lower() in EXT_EXCLUDE:
        return True
    # exclusions spécifiques
    if rel.name in {"db.sqlite3"}:
        return False
    return False

def sanity_checks(root: Path) -> list[str]:
    issues = []
    if not (root / "manage.py").exists():
        issues.append("manage.py introuvable à la racine.")

    settings_pkg = root / "systeme_reservation_plateforme" / "settings"
    if not settings_pkg.exists():
        issues.append("Le dossier systeme_reservation_plateforme/settings/ est introuvable.")

    # requirements / pyproject
    if not (root / "requirements.txt").exists() and not (root / "pyproject.toml").exists():
        issues.append("requirements.txt (ou pyproject.toml) manquant — nécessaire pour pip install.")

    # migrations (vérif simple)
    has_migrations = any(p.name == "migrations" for p in root.rglob("migrations"))
    if not has_migrations:
        issues.append("None 'migrations/' détectée dans les apps — attention au schéma DB en prod.")

    # .env templates conseillés
    for env_name in ENV_INCLUDE:
        if not (root / env_name).exists():
            issues.append(f"{env_name} manquant (conseillé).")

    return issues


def pack(root: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = root / f"Calendrier_reservation_pack_{ts}.zip"
    total_bytes = 0
    files_count = 0

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in root.rglob("*"):
            if p.is_dir():
                continue
            rel = p.relative_to(root)
            if p == zip_path:
                continue
            if should_exclude(p, rel):
                continue
            z.write(p, arcname=str(rel))
            files_count += 1
            try:
                total_bytes += p.stat().st_size
            except Exception:
                pass

    print(f"✅ Archive créée : {zip_path}")
    print(f"   → {files_count} fichiers, ~{round(total_bytes/1024/1024, 2)} Mo")
    return zip_path

if __name__ == "__main__":
    start = Path.cwd()
    root = find_project_root(start)
    if not root:
        print("❌ Impossible de trouver la racine du projet (manage.py). Lance le script depuis n’importe où DANS le repo.")
        sys.exit(1)

    print(f"📍 Racine détectée : {root}")

    problems = sanity_checks(root)
    if problems:
        print("⚠️ Vérifications :")
        for msg in problems:
            print("  - " + msg)
        # on continue quand même pour que tu voies ce qui manquerait

    zip_path = pack(root)
    print("ℹ️ Astuce : lance ce script depuis n’importe où dans le projet, il détectera la racine automatiquement.")


