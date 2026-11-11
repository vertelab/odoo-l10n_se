# -*- coding: utf-8 -*-
# Copyright (C) 2026- Vertel Sverige AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Move res.company.vat_report_template_id from mis.report to account.report.

The column type changes from many2one(mis.report) to many2one(account.report),
so the old ids are meaningless in the new table. Rather than leaving stale ids
pointing at unrelated reports, every company that had a template configured is
re-pointed at the Swedish tax report -- which is what the old MIS template
computed anyway.

WHY THIS RUNS IN TWO STEPS
--------------------------
The re-pointing reads ir.model.data to find the new reports. Those xmlids are
declared in this module's own data files, and data files load AFTER
pre-migrate. In a pre-migrate the lookup therefore finds nothing, and worse:
the old integer is already sitting in a column that now has a foreign key to
account.report, so an id that no longer exists aborts the whole upgrade
(measured on odoo-sfa-ce-18-se-staging 2026-11-11: mis.report 16/28 resolved to
account.report ids that did not exist -> ForeignKeyViolation).

So:
  pre-migrate   detach the stale value -- set the column to NULL while the
                old ids are still meaningless. Nothing to resolve yet.
  post-migrate  re-point at the new reports, which now exist.

WHO GETS RE-POINTED
-------------------
Only companies whose column was set on entry. The pre-migrate records those
row ids in a temporary table so the post-migrate knows which companies actually
had a template, rather than blanket-assigning one to everyone. A company with
no template configured stays empty -- we do not invent a setting nobody chose.

IDEMPOTENT: every step is a no-op on a second run. The temp table is dropped in
both migrations.
"""

import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

# Field on res.company -> xmlid of the account.report that replaces the old
# MIS template. Resolved in the post-migrate, when the xmlids exist.
FIELD_TO_REPORT = {
    "vat_report_template_id": "l10n_se.tax_report",
    "pc_report_template_id": "l10n_se_tax_report.periodic_compilation_report",
}

# Temporary table carrying the re-pointing work across the two phases.
QUEUE_TABLE = "_l10n_se_tax_report_retemplate"


def _column_exists(cr, field):
    cr.execute(
        """
        SELECT 1 FROM information_schema.columns
         WHERE table_name = 'res_company' AND column_name = %s
        """,
        (field,),
    )
    return bool(cr.fetchone())


def _account_report_id(env, xmlid):
    """Resolve an account.report xmlid to its id, or None if not present."""
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
    """Phase 1: detach the stale MIS ids before the column type changes."""
    if not version:
        return

    fields = [f for f in FIELD_TO_REPORT if _column_exists(cr, f)]
    if not fields:
        _logger.info(
            "l10n_se_tax_report: no report-template columns on res_company."
        )
        return

    # Remember who had a template configured. Without this the post-migrate
    # cannot tell "was configured with a MIS template" (re-point it) from
    # "was empty" (leave it alone).
    cr.execute("DROP TABLE IF EXISTS %s" % QUEUE_TABLE)
    cr.execute(
        "CREATE TABLE %s (company_id integer NOT NULL, field varchar NOT NULL)"
        % QUEUE_TABLE
    )
    for field in fields:
        cr.execute(
            """
            INSERT INTO %s (company_id, field)
            SELECT id, %%s FROM res_company WHERE %s IS NOT NULL
            """
            % (QUEUE_TABLE, field),
            (field,),
        )
        configured = cr.rowcount
        cr.execute(
            "UPDATE res_company SET %s = NULL WHERE %s IS NOT NULL"
            % (field, field)
        )
        _logger.info(
            "l10n_se_tax_report pre-migrate: detached %s on %d "
            "company/companies; the post-migrate will re-point them.",
            field,
            configured,
        )
