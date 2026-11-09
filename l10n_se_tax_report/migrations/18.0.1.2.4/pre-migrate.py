# -*- coding: utf-8 -*-
# Copyright (C) 2026- Vertel Sverige AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Move res.company.vat_report_template_id from mis.report to account.report.

The column type changes from many2one(mis.report) to many2one(account.report),
so the old ids are meaningless in the new table. Rather than leaving stale ids
pointing at unrelated reports, every company that had a template configured is
re-pointed at the Swedish tax report -- which is what the old MIS template
computed anyway.
"""

import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    cr.execute("""
        SELECT column_name, data_type
          FROM information_schema.columns
         WHERE table_name = 'res_company'
           AND column_name = 'vat_report_template_id'
    """)
    row = cr.fetchone()
    if not row:
        return

    # How many companies had a template configured?
    cr.execute("SELECT count(*) FROM res_company WHERE vat_report_template_id IS NOT NULL")
    configured = cr.fetchone()[0]
    _logger.info(
        "l10n_se_tax_report: %s company/companies had a MIS VAT template; "
        "re-pointing them at the Swedish account.report.", configured)
