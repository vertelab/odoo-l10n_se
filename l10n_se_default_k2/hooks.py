# -*- coding: utf-8 -*-
"""Applicera K2-kontoplanen pa foretag som saknar en riktig plan.

BAKGRUND (2026-10-29)
=====================
`extended_se_K2` registreras via @template-dekoratorn i
l10n_se_extended/models/template_se_K2.py, men ingenting satte den som
default. Ett nytt foretag fick `generic_coa` (52 engelska konton) i
stallet for Vertels K2-plan (1192 svenska BAS-konton).

FALLAN: foretagets land ar inte alltid SE nar modulen installeras. I
template_base-klonen star det kvar som US (Odoos default) aven om
installationsguiden senare satter SE. Att kravla pa country_id.code ==
"SE" gjorde att hooken tyst hoppade over — och kvar blev generic_coa.

Logiken ar darfor: applicera K2 om foretaget antingen ar svenskt ELLER
saknar en riktig kontoplan (generic_coa/False) och inte har nagra
bokforingsposter an.
"""
import logging

_logger = logging.getLogger(__name__)

DEFAULT_CHART = "extended_se_K2"
SE_COUNTRY = "SE"


def _apply_default_chart(env, source="l10n_se_default_k2"):
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
