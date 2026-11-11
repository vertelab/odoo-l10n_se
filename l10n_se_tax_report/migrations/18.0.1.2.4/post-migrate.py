# -*- coding: utf-8 -*-
# Copyright (C) 2026- Vertel Sverige AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Phase 2 of the vat_report_template_id move: re-point at account.report.

The pre-migrate detached the stale MIS ids (they are meaningless once the
column points at account.report) and recorded which companies had one. Now
that this module's data files have loaded, the target reports exist and the
values can be restored -- pointing at something real.

A company whose template is missing from the data files is logged and left
empty. Guessing an id would put an unrelated report in the tax declaration
setting, which is worse than an empty field the user can fill in.
"""

import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

FIELD_TO_REPORT = {
    "vat_report_template_id": "l10n_se.tax_report",
    "pc_report_template_id": "l10n_se_tax_report.periodic_compilation_report",
}

QUEUE_TABLE = "_l10n_se_tax_report_retemplate"


def _queue_exists(cr):
    cr.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_name = %s",
        (QUEUE_TABLE,),
    )
    return bool(cr.fetchone())


def _account_report_id(env, xmlid):
    module, name = xmlid.split(".", 1)
    record = env["ir.model.data"].search(
        [
            ("module", "=", module),
            ("name", "=", name),
            ("model", "=", "account.report"),
        ],
        limit=1,
    )
    return record.res_id if record else None


def migrate(cr, version):
    """Phase 2: re-point the companies the pre-migrate detached."""
    if not _queue_exists(cr):
        # Fresh install, or the pre-migrate did not run. Nothing to restore.
        _logger.info(
            "l10n_se_tax_report post-migrate: no re-pointing queue, skipping."
        )
        return

    env = api.Environment(cr, SUPERUSER_ID, {})

    for field, xmlid in FIELD_TO_REPORT.items():
        cr.execute(
            "SELECT DISTINCT company_id FROM %s WHERE field = %%s" % QUEUE_TABLE,
            (field,),
        )
        company_ids = [row[0] for row in cr.fetchall()]
        if not company_ids:
            continue

        target_id = _account_report_id(env, xmlid)
        if not target_id:
            _logger.warning(
                "l10n_se_tax_report post-migrate: account.report %s not "
                "found; leaving %s empty on %d company/companies rather "
                "than guessing an id.",
                xmlid,
                field,
                len(company_ids),
            )
            continue

        cr.execute(
            "UPDATE res_company SET %s = %%s WHERE id = ANY(%%s)"
            % field,
            (target_id, company_ids),
        )
        _logger.info(
            "l10n_se_tax_report post-migrate: re-pointed %s on %d "
            "company/companies at account.report %s (id %s).",
            field,
            cr.rowcount,
            xmlid,
            target_id,
        )

    cr.execute("DROP TABLE IF EXISTS %s" % QUEUE_TABLE)
