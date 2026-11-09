# -*- coding: utf-8 -*-
# Copyright (C) 2026- Vertel Sverige AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Detach the old MIS report instances before the data files disappear.

Same situation as l10n_se_mis: the MIS XML data files are gone, so Odoo
deletes the mis.report records, but mis.report.instance still points at them
with a foreign key and the upgrade aborts. The instances are saved report
views, not accounting data, so removing them is safe.
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    cr.execute("""
        SELECT res_id FROM ir_model_data
         WHERE model = 'mis.report' AND module = 'l10n_se_mis_k3_koncern'
    """)
    report_ids = [row[0] for row in cr.fetchall()]
    if not report_ids:
        _logger.info("l10n_se_mis_k3_koncern: no legacy MIS reports to detach.")
        return

    cr.execute("DELETE FROM mis_report_instance WHERE report_id = ANY(%s)",
               (report_ids,))
    _logger.info(
        "l10n_se_mis_k3_koncern 18.0.2.0.0: removed %d legacy MIS report instances.",
        cr.rowcount)
