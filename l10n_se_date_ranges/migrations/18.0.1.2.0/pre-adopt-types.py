# -*- coding: utf-8 -*-
"""Adopt the quarter and week date range types from the retired bridge.

``l10n_se_account_fiscal_year`` used to own all four ``date.range.type``
records. Ownership is now split: ``account_fiscal_year_vrtl`` owns Fiscal
Year and Month, this module owns Quarter and Week.

This migration re-points the ``ir.model.data`` rows for the two types this
module now owns. Moving the row (not the record) keeps ``res_id`` intact, so
every ``date.range.type_id`` keeps pointing at the same record.

Why a migration script and not pre_init_hook: ``pre_init_hook`` only runs on
install, never on upgrade (``odoo/modules/loading.py``).

This module is installed *after* ``account_fiscal_year_vrtl`` because it
depends on it, so the fiscal year / month adoption has already happened when
this runs.
"""
import logging

_logger = logging.getLogger(__name__)

LEGACY_MODULE = "l10n_se_account_fiscal_year"
OWNED_XMLIDS = (
    "date_range_type_quarter",
    "date_range_type_week",
)


def migrate(cr, version):
    if not version:
        return

    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    Imd = env["ir.model.data"].sudo()

    adopted = 0
    for name in OWNED_XMLIDS:
        legacy = Imd.search([
            ("module", "=", LEGACY_MODULE),
            ("name", "=", name),
            ("model", "=", "date.range.type"),
        ], limit=1)
        if not legacy:
            continue
        already = Imd.search([
            ("module", "=", "l10n_se_date_ranges"),
            ("name", "=", name),
            ("model", "=", "date.range.type"),
        ], limit=1)
        if already:
            continue
        legacy.write({"module": "l10n_se_date_ranges"})
        adopted += 1
        _logger.info(
            "Adopted date range type %s from %s (res_id %s).",
            name, LEGACY_MODULE, legacy.res_id,
        )

    _logger.info(
        "l10n_se_date_ranges 18.0.1.2.0: adopted %d date range type(s) from %s.",
        adopted, LEGACY_MODULE,
    )
