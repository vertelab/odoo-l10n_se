# -*- coding: utf-8 -*-
"""Applicera K2-kontoplanen pa foretag som saknar en riktig plan.

BAKGRUND (2026-10-29, rattad 2026-10-30)
========================================
Odoo 18:s inbyggda `l10n_se` registrerar kompletta svenska
BAS-kontoplaner som chart templates:

    se      - Sverige (rot)
    se_K2   - BAS komplett K2   (1175 konton)
    se_K3   - BAS komplett K3   (1201 konton, parent se_K2)

Men ingenting satte dem som default. Ett nytt foretag med land SE fick
`generic_coa` (51 engelska konton med 6-siffriga koder) i stallet for
BAS-planen.

RATTELSE 2026-10-30: den har hooken pekade tidigare pa `extended_se_K2`,
som deklareras i l10n_se_extended/models/template_se_K2.py via
@template-dekoratorn men ALDRIG registreras i Odoo 18:s template-API.
`try_loading` kastade KeyError, hooken fangade undantaget och loggade
"fick kontoplan" trots att ingenting hande — sa den gjorde i praktiken
ingenting alls. Nu pekar den pa core:s `se_K2`, och den verifierar
resultatet efterat sa den aldrig kan rapportera falsk framgang igen.

FALLAN: foretagets land ar inte alltid SE nar modulen installeras. I
template_base-klonen star det kvar som US (Odoos default) aven om
installationsguiden senare satter SE. Att kravla pa country_id.code ==
"SE" gjorde att hooken tyst hoppade over — och kvar blev generic_coa.

Logiken ar darfor: applicera K2 om foretaget antingen ar svenskt ELLER
saknar en riktig kontoplan (generic_coa/False) och inte har nagra
bokforingsposter an.

K2 ELLER K3 (2026-10-30)
========================
Den har hooken ligger i l10n_se_extended, som bada regelverken bygger
pa. Nar l10n_se_extended installeras ensam ar K2 ratt default (de flesta
bolag). Men om l10n_se_default_k3 finns installerad eller redan ar pa
vag in i samma installation, ska K3 vinna — annars satter vi K2 forst
och K3-hooken hittar en "riktig" plan och ror den inte.

Losningen: om modulen l10n_se_default_k3 finns i registret och inte ar
avinstallerad, hoppar den har hooken over helt. K3-modulens egen
post_init_hook gor jobbet i stallet.
"""
import logging

_logger = logging.getLogger(__name__)

DEFAULT_CHART = "se_K2"
K3_OVERRIDE_MODULE = "l10n_se_default_k3"
SE_COUNTRY = "SE"


def _k3_takes_over(env):
    """Returnerar True om l10n_se_default_k3 ska aga kontoplansvalet."""
    module = env["ir.module.module"].search(
        [("name", "=", K3_OVERRIDE_MODULE)], limit=1)
    if not module:
        return False
    # 'to install'/'to upgrade' raknas ocksa - modulen kan ligga i samma
    # checkmodule-korning och annta inte vara installerad an.
    return module.state in ("installed", "to install", "to upgrade")


def _apply_default_chart(env, source="l10n_se_extended"):
    if _k3_takes_over(env):
        _logger.info(
            "%s: %s hanterar kontoplanen - hoppar over K2.",
            source, K3_OVERRIDE_MODULE)
        return

    company_model = env["res.company"]
    chart_model = env["account.chart.template"]

    available = chart_model._get_chart_template_mapping()
    if DEFAULT_CHART not in available:
        _logger.warning(
            "%s: kontoplanen %s finns inte i registret - hoppar over.",
            source, DEFAULT_CHART)
        return

    for company in company_model.search([]):
        current = company.chart_template
        country = company.country_id.code

        # Redan satt till en riktig plan? Lat den vara.
        if current and current not in ("generic_coa", False):
            _logger.info(
                "%s: %s har redan kontoplan %s - ror den inte.",
                source, company.name, current)
            continue

        # Inte svenskt OCH har redan en plan? Lat den vara.
        if country != SE_COUNTRY and current not in ("generic_coa", False):
            _logger.info(
                "%s: %s har land %s och kontoplan %s - ror den inte.",
                source, company.name, country, current)
            continue

        # Har foretaget redan bokforingsposter? Da ar det for sent att byta.
        moves = env["account.move"].search_count([("company_id", "=", company.id)])
        if moves:
            _logger.info(
                "%s: %s har %s bokforingsposter - applicerar inte %s.",
                source, company.name, moves, DEFAULT_CHART)
            continue

        try:
            _logger.info(
                "%s: applicerar %s pa %s (land=%s, nuvarande=%s)",
                source, DEFAULT_CHART, company.name, country, current)
            chart_model.try_loading(DEFAULT_CHART, company, install_demo=False)
        except Exception as exc:  # noqa: BLE001 - hooken far aldrig blockera installation
            _logger.warning(
                "%s: kunde inte applicera %s pa %s: %s",
                source, DEFAULT_CHART, company.name, exc)
            continue

        # Verifiera - try_loading kan returnera utan att ha gjort nagot.
        company.invalidate_recordset(["chart_template"])
        applied = company.chart_template
        if applied == DEFAULT_CHART:
            _logger.info(
                "%s: %s fick kontoplan %s", source, company.name, applied)
        else:
            _logger.error(
                "%s: applicerade %s pa %s men chart_template ar fortfarande "
                "%s - kontoplanen laddades inte.",
                source, DEFAULT_CHART, company.name, applied)


def post_init_hook(env):
    _apply_default_chart(env)
