# -*- coding: utf-8 -*-
"""Applicera K3-kontoplanen pa foretag som saknar en riktig plan.

BAKGRUND (2026-10-30)
=====================
Odoo 18:s inbyggda `l10n_se` registrerar redan kompletta svenska
BAS-kontoplaner som chart templates:

    se      - Sverige (rot)
    se_K2   - BAS komplett K2   (1175 konton)
    se_K3   - BAS komplett K3   (1201 konton, parent se_K2)

Men ingenting satte dem som default. Ett nytt foretag med land SE fick
`generic_coa` (51 engelska konton med 6-siffriga koder) i stallet for
BAS-planen.

K3-planen skiljer sig fran K2 pa punkter som spelar roll for
arsredovisningen: uppskjuten skatt (1370/2240/2250), K3:s eget
kapital-fonder (2092/2096), utvecklingsutgifter (1010-1019/1081/1088),
och de finansiella 8xxx-serierna (8290/8320/8450/8480).
K2-planen saknar dessa.

FALLAN: foretagets land ar inte alltid SE nar modulen installeras. I
template_base-klonen star det kvar som US (Odoos default) aven om
installationsguiden senare satter SE. Att kravla pa country_id.code ==
"SE" gjorde att hooken tyst hoppade over.

Logiken ar darfor: applicera K3 om foretaget antingen ar svenskt ELLER
saknar en riktig kontoplan (generic_coa/False) och inte har nagra
bokforingsposter an.

ANVANDNING: den har modulen ar ALTERNATIV till l10n_se_default_k2 -
ett bolag tillampar antingen K2 eller K3, aldrig bada. Installera
endast en av dem per databas.
"""
import logging

_logger = logging.getLogger(__name__)

DEFAULT_CHART = "se_K3"
SE_COUNTRY = "SE"


def _apply_default_chart(env, source="l10n_se_default_k3"):
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
            _logger.info(
                "%s: %s fick kontoplan %s", source, company.name, DEFAULT_CHART)
        except Exception as exc:  # noqa: BLE001 - hooken far aldrig blockera installation
            _logger.warning(
                "%s: kunde inte applicera %s pa %s: %s",
                source, DEFAULT_CHART, company.name, exc)


def post_init_hook(env):
    _apply_default_chart(env)
