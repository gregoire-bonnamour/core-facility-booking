# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NoCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

from django.http import JsonResponse
from django.db import connections
from django.db.utils import OperationalError

def healthz(request):
    # Liveness: le process Django répond
    return JsonResponse({"status": "ok"})

def readyz(request):
    # Readiness: test rapide DB by default
    db_conn = connections["default"]
    try:
        db_conn.cursor()
        return JsonResponse({"status": "ok"})
    except OperationalError:
        return JsonResponse({"status": "db_unavailable"}, status=503)
