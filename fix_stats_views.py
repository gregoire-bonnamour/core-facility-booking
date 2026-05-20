"""
Script de patch pour reserv/views.py et reserv/urls.py
- Simplification de stats_query (suppression par_aff, par_fct, utilisation)
- Ajout de stats_zone1
- Mise a jour urls.py
"""
import re, os, sys

BASE = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# 1. PATCH views.py
# ============================================================
views_path = os.path.join(BASE, "booking", "views.py")
with open(views_path, "r", encoding="utf-8") as f:
    src = f.read()

# -- 1a. Changer @require_POST -> @require_http_methods(["GET","POST"]) sur stats_query
old_decorator = (
    "@login_required\n"
    "@user_passes_test(est_admin_plateforme)\n"
    "@csrf_protect\n"
    "@require_POST\n"
    "def stats_query(request):"
)
new_decorator = (
    "@login_required\n"
    "@user_passes_test(est_admin_plateforme)\n"
    "def stats_query(request):"
)
assert old_decorator in src, "ERREUR: bloc decorator stats_query introuvable"
src = src.replace(old_decorator, new_decorator, 1)
print("OK: decorator stats_query mis a jour")

# -- 1b. Supprimer par_aff et par_fct des defaultdicts
old_dicts = (
    "    par_aff = defaultdict(lambda: {'reservations': 0, 'min_usage': 0, 'min_assist': 0})\n"
    "    par_labo= defaultdict(lambda: {'reservations': 0, 'min_usage': 0, 'min_assist': 0})\n"
    "    par_fct = defaultdict(lambda: {'reservations': 0, 'min_usage': 0, 'min_assist': 0})\n"
    "    par_usr = defaultdict(lambda: {'reservations': 0, 'min_usage': 0, 'min_assist': 0})"
)
new_dicts = (
    "    par_labo= defaultdict(lambda: {'reservations': 0, 'min_usage': 0, 'min_assist': 0})\n"
    "    par_usr = defaultdict(lambda: {'reservations': 0, 'min_usage': 0, 'min_assist': 0})"
)
assert old_dicts in src, "ERREUR: bloc defaultdicts stats_query introuvable"
src = src.replace(old_dicts, new_dicts, 1)
print("OK: par_aff et par_fct supprimes des defaultdicts")

# -- 1c. Supprimer l'alimentation de par_aff dans le loop
old_aff_block = (
    "        aff = getattr(getattr(getattr(r, 'accounts', None), 'laboratoire', None), 'affiliation', None)\n"
    "        if aff:\n"
    "            key = (aff.id, aff.nom)\n"
    "            par_aff[key]['reservations'] += 1\n"
    "            par_aff[key]['min_usage']    += mu\n"
    "            par_aff[key]['min_assist']   += ma\n"
    "\n"
    "        if getattr(r, 'accounts', None) and getattr(r.usager, 'laboratoire', None):"
)
new_aff_block = (
    "        if getattr(r, 'accounts', None) and getattr(r.usager, 'laboratoire', None):"
)
assert old_aff_block in src, "ERREUR: bloc par_aff loop introuvable"
src = src.replace(old_aff_block, new_aff_block, 1)
print("OK: alimentation par_aff supprimee du loop")

# -- 1d. Supprimer l'alimentation de par_fct dans le loop
old_fct_block = (
    "        if getattr(r, 'accounts', None) and getattr(r.usager, 'fonction', None):\n"
    "            key = (r.usager.fonction.id, r.usager.fonction.nom)\n"
    "            par_fct[key]['reservations'] += 1\n"
    "            par_fct[key]['min_usage']    += mu\n"
    "            par_fct[key]['min_assist']   += ma\n"
    "\n"
    "        if getattr(r, 'accounts', None):"
)
new_fct_block = (
    "        if getattr(r, 'accounts', None):"
)
assert old_fct_block in src, "ERREUR: bloc par_fct loop introuvable"
src = src.replace(old_fct_block, new_fct_block, 1)
print("OK: alimentation par_fct supprimee du loop")

# -- 1e. Mettre a jour le dict tables (supprimer affiliations et fonctions)
old_tables = (
    "    tables = {\n"
    "        'equipment':  _tabify(par_eq),\n"
    "        'affiliations': _tabify(par_aff),\n"
    "        'laboratoires': _tabify(par_labo),\n"
    "        'fonctions':    _tabify(par_fct),\n"
    "        'usagers':      _tabify(par_usr),\n"
    "    }"
)
new_tables = (
    "    tables = {\n"
    "        'equipment':  _tabify(par_eq),\n"
    "        'laboratoires': _tabify(par_labo),\n"
    "        'usagers':      _tabify(par_usr),\n"
    "    }"
)
assert old_tables in src, "ERREUR: dict tables stats_query introuvable"
src = src.replace(old_tables, new_tables, 1)
print("OK: dict tables simplifie")

# -- 1f. Supprimer le bloc utilisation (taux d'occupation)
old_util = (
    "    eq_ids = filters.get('equipment') or list({r.equipement_id for r in resas if r.equipement_id})\n"
    "    eqs = Equipement.objects.filter(id__in=eq_ids).prefetch_related('creneaux').order_by('nom') if eq_ids else []\n"
    "\n"
    "    utilisation = []\n"
    "    for e in eqs:\n"
    "        available_min = 0\n"
    "        for c in e.creneaux.all():\n"
    "            slot_min = int((_combine_safe(date.today(), c.heure_fin) - _combine_safe(date.today(), c.heure_debut)).total_seconds() // 60)\n"
    "            available_min += wd_counts.get(int(c.jour), 0) * max(slot_min, 0)\n"
    "\n"
    "        used_min = sum(minutes_resa(r) for r in resas if r.equipement_id == e.id)\n"
    "        pct = round(100.0 * used_min / available_min, 1) if available_min > 0 else 0.0\n"
    "        utilisation.append({\n"
    "            'equipement_id': e.id,\n"
    "            'equipement': e.nom,\n"
    "            'heures_utilisees': round(used_min/60.0, 2),\n"
    "            'heures_disponibles': round(available_min/60.0, 2),\n"
    "            'occupation_pct': pct,\n"
    "        })\n"
    "\n"
    "    kpis = {"
)
new_util = "    kpis = {"
assert old_util in src, "ERREUR: bloc utilisation introuvable"
src = src.replace(old_util, new_util, 1)
print("OK: bloc utilisation supprime")

# -- 1g. Supprimer 'utilisation' du JsonResponse
old_json = (
    "    return JsonResponse({\n"
    "        'ok': True,\n"
    "        'kpis': kpis,\n"
    "        'tables': tables,\n"
    "        'timeseries': {'weekly': ts_weekly},\n"
    "        'utilisation': utilisation,\n"
    "    })"
)
new_json = (
    "    return JsonResponse({\n"
    "        'ok': True,\n"
    "        'kpis': kpis,\n"
    "        'tables': tables,\n"
    "        'timeseries': {'weekly': ts_weekly},\n"
    "    })"
)
assert old_json in src, "ERREUR: JsonResponse stats_query introuvable"
src = src.replace(old_json, new_json, 1)
print("OK: utilisation retire du JsonResponse")

# -- 1h. Ajouter stats_zone1 avant la palette de couleurs
stats_zone1_code = '''
@login_required
@user_passes_test(est_admin_plateforme)
def stats_zone1(request):
    """
    Statistiques globales plateforme (zone 1) :
    - Nombre d usagers actifs
    - Nombre de laboratoires representes (au moins un usager actif)
    - Nombre de nouveaux inscrits sur la periode (reglement accepte)
    """
    from accounts.models import Usager, Laboratoire

    def _parse(s):
        try:
            return datetime.strptime(s, "%Y-%m-%d").date() if s else None
        except Exception:
            return None

    debut = _parse(request.GET.get("date_debut") or "")
    fin   = _parse(request.GET.get("date_fin") or "")

    nb_actifs = Usager.objects.filter(est_actif=True).count()
    nb_labos  = Laboratoire.objects.filter(usager__est_actif=True).distinct().count()

    qs_inscrits = Usager.objects.filter(reglement_accepte=True)
    if debut:
        qs_inscrits = qs_inscrits.filter(reglement_accepte_at__date__gte=debut)
    if fin:
        qs_inscrits = qs_inscrits.filter(reglement_accepte_at__date__lte=fin)
    nb_inscrits = qs_inscrits.count()

    return JsonResponse({
        "usagers_actifs":    nb_actifs,
        "labos_representes": nb_labos,
        "nouveaux_inscrits": nb_inscrits,
    })

'''

old_palette = (
    "# Palette discrete (10 couleurs): on re-map par id d equipement"
)
# Le commentaire dans le fichier utilise accent : cherchons la vraie version
palette_marker = "PALETTE = ["
assert palette_marker in src, "ERREUR: PALETTE introuvable dans views.py"
src = src.replace(palette_marker, stats_zone1_code + palette_marker, 1)
print("OK: stats_zone1 ajoute")

with open(views_path, "w", encoding="utf-8") as f:
    f.write(src)
print("OK: views.py sauvegarde")

# ============================================================
# 2. PATCH urls.py
# ============================================================
urls_path = os.path.join(BASE, "booking", "urls.py")
with open(urls_path, "r", encoding="utf-8") as f:
    urls = f.read()

old_stats_url = "    path('stats/query/', views.stats_query, name='stats_query'),"
new_stats_url = (
    "    path('stats/query/', views.stats_query, name='stats_query'),\n"
    "    path('stats/zone1/', views.stats_zone1, name='stats_zone1'),"
)
assert old_stats_url in urls, "ERREUR: URL stats_query introuvable dans urls.py"
urls = urls.replace(old_stats_url, new_stats_url, 1)

with open(urls_path, "w", encoding="utf-8") as f:
    f.write(urls)
print("OK: urls.py mis a jour")

print("\nPatch termine avec succes.")
