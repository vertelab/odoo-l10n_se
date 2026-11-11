# -*- coding: utf-8 -*-
# Copyright (C) 2026- Vertel Sverige AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Detach the old MIS report instances before the data files disappear.

The XML data files that defined the MIS Builder reports are gone in this
version. Odoo removes records whose xmlid no longer exists, but
``mis.report.instance`` rows still point at them with a foreign key, so the
delete fails and the whole upgrade aborts.

The instances are historical artefacts of the old reports. They are unlinked
here (they carry no accounting data -- a MIS instance is a saved report view),
after which Odoo can remove the reports themselves.
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    # Reports this module used to ship.
    cr.execute("""
        SELECT res_id FROM ir_model_data
         WHERE model = 'mis.report' AND module = 'l10n_se_mis'
    """)
    report_ids = [row[0] for row in cr.fetchall()]
    if not report_ids:
        _logger.info("l10n_se_mis: no legacy MIS reports to detach.")
        return

    # Delete children before parents. mis_report_instance_period_sum has
    # ON DELETE RESTRICT on period_to_sum_id, so a plain DELETE on
    # mis_report_instance aborts with ForeignKeyViolation when any instance
    # has a column that sums another column (verified on
    # odoo-sfa-ce-18-se-staging 2026-11-11: 2 rows blocked 52 instances).
    cr.execute("""
        SELECT id FROM mis_report_instance WHERE report_id = ANY(%s)
    """, (report_ids,))
    instance_ids = [row[0] for row in cr.fetchall()]
    if instance_ids:
        cr.execute("""
            DELETE FROM mis_report_instance_period_sum
             WHERE period_to_sum_id IN (
                   SELECT id FROM mis_report_instance_period
                    WHERE report_instance_id = ANY(%s))
        """, (instance_ids,))
        _logger.info(
            "l10n_se_mis 18.0.2.0.0: removed %d period-sum rows first "
            "(ON DELETE RESTRICT would otherwise abort).", cr.rowcount)
        cr.execute("""
            DELETE FROM mis_report_instance_period
             WHERE report_instance_id = ANY(%s)
        """, (instance_ids,))
        _logger.info(
            "l10n_se_mis 18.0.2.0.0: removed %d periods.", cr.rowcount)

    cr.execute("""
        DELETE FROM mis_report_instance
         WHERE report_id = ANY(%s)
    """, (report_ids,))
    removed_instances = cr.rowcount
    _logger.info(
        "l10n_se_mis 18.0.2.0.0: removed %d legacy MIS report instances so the "
        "old mis.report records can be deleted.", removed_instances)
