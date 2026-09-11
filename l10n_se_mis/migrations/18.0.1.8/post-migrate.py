# -*- coding: utf-8 -*-
"""Clean up balance-sheet KPI records and reset their noupdate flag.

Background
----------
mis_financial_report.xml used to be loaded with noupdate="1". Odoo persists the
noupdate flag *per record* in ir_model_data on first load, so flipping the XML
attribute alone is not enough: existing rows keep noupdate=t and are never
overwritten by later upgrades. This migration resets the flag for the balance
sheet records so the following data-file load actually applies the new values.

It also removes orphaned mis.report.kpi records: rows that existed in an earlier
version of the file but have since been deleted from it.

Runs once per database (Odoo only executes migrations/<version>/ when
ir_module_module.latest_version < the manifest version).
"""
import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

# xmlid prefix for records defined in mis_financial_report.xml
XMLID_MODULE = "l10n_se_mis"
REPORT_XMLID = "l10n_se_mis.report_br"


def migrate(cr, version):
    if not version:
        # Fresh install - nothing to clean up.
        return

    env = api.Environment(cr, SUPERUSER_ID, {})

    # -- 1. Reset noupdate for the balance sheet records ---------------------
    # Without this Odoo will not overwrite existing rows, regardless of what
    # the data file says.
    report = env.ref(REPORT_XMLID, raise_if_not_found=False)
    if not report:
        _logger.warning(
            "l10n_se_mis: %s not found - skipping KPI cleanup.",
            REPORT_XMLID,
        )
        return

    kpis = env["mis.report.kpi"].search([("report_id", "=", report.id)])
    if not kpis:
        return

    # xmlids actually defined in the data file (loaded by this module)
    data = env["ir.model.data"].search_read(
        [
            ("module", "=", XMLID_MODULE),
            ("model", "=", "mis.report.kpi"),
        ],
        ["res_id", "name", "noupdate"],
    )
    defined_ids = {rec["res_id"] for rec in data}

    # Reset noupdate on every KPI belonging to the balance sheet
    locked = env["ir.model.data"].search(
        [
            ("module", "=", XMLID_MODULE),
            ("model", "=", "mis.report.kpi"),
            ("res_id", "in", kpis.ids),
            ("noupdate", "=", True),
        ]
    )
    if locked:
        _logger.info(
            "l10n_se_mis: resetting noupdate for %d balance sheet KPIs so the "
            "data file can overwrite them.",
            len(locked),
        )
        locked.write({"noupdate": False})

    # Expressions have their own xmlids - reset those too
    expr_xmlids = env["ir.model.data"].search(
        [
            ("module", "=", XMLID_MODULE),
            ("model", "=", "mis.report.kpi.expression"),
            ("noupdate", "=", True),
        ]
    )
    if expr_xmlids:
        _logger.info(
            "l10n_se_mis: resetting noupdate for %d KPI expressions.",
            len(expr_xmlids),
        )
        expr_xmlids.write({"noupdate": False})

    # -- 2. Remove orphaned KPIs ---------------------------------------------
    orphans = kpis.filtered(lambda k: k.id not in defined_ids)
    if not orphans:
        _logger.info(
            "l10n_se_mis: no orphaned balance sheet KPIs - nothing to clean up."
        )
        return

    _logger.info(
        "l10n_se_mis: removing %d orphaned balance sheet KPIs: %s",
        len(orphans),
        ", ".join(orphans.mapped("name")),
    )

    # Expressions normally cascade via ondelete, but be explicit so this stays
    # correct even if the FK rule changes.
    env["mis.report.kpi.expression"].search(
        [("kpi_id", "in", orphans.ids)]
    ).unlink()
    orphans.unlink()
