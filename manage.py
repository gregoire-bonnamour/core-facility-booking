# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NoCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

# 👉 Point unique de vérité : on force les settings de dev by default.
os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "systeme_reservation_plateforme.settings.local"
)

def main():
    """Run administrative tasks."""
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)

if __name__ == "__main__":
    main()
