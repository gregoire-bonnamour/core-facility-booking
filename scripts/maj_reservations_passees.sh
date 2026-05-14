# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# Active le venv si tu en as un
if [ -d ".venv" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

# Charge .env pour les vars (si tu utilises django-environ / python-dotenv, ce n'est pas nécessaire)
# export $(grep -v '^#' .env | xargs) 2>/dev/null || true

python manage.py maj_reservations_passees
