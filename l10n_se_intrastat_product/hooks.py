# -*- coding: utf-8 -*-
# Copyright 2026 Vertel Sverige AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Swedish Intrastat always includes accessory costs.

    The statistical value is the market value of the goods at the Swedish
    border, delivery costs (freight, packaging, insurance) included — SCB
    Handledning 2026, section 7. The OCA setting defaults to off, which would
    silently drop those costs from the declaration, so it is switched on for
    every company on install.
    """
    companies = env["res.company"].search([])
    to_fix = companies.filtered(lambda c: not c.intrastat_accessory_costs)
    if to_fix:
        to_fix.write({"intrastat_accessory_costs": True})
        _logger.info(
            "Intrastat (SCB): enabled accessory costs on %s company/companies",
            len(to_fix),
        )
