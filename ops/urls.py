# Copyright (c) 2025 Author Author
# Licensed under the Creative Commons Attribution-NoCommercial 4.0 International License (CC BY-NC 4.0)
# See the LICENSE file or https://creativecommons.org/licenses/by-nc/4.0/legalcode for details.

from django.urls import path
from . import views

urlpatterns = [
    path("healthz", views.healthz),
    path("readyz", views.readyz),
]
