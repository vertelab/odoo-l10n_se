# -*- coding: utf-8 -*-
# Copyright 2026 Vertel AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)

# Swedish Intrastat thresholds (2024)
# Arrivals: 12 MSEK → standard, 550 MSEK → extended
# Dispatches: 5 MSEK → standard, 275 MSEK → extended
SE_ARRIVALS_THRESHOLD = 12_000_000
SE_ARRIVALS_EXTENDED_THRESHOLD = 550_000_000
SE_DISPATCHES_THRESHOLD = 5_000_000
SE_DISPATCHES_EXTENDED_THRESHOLD = 275_000_000


class ResCompany(models.Model):
    _inherit = "res.company"

    intrastat_accessory_costs = fields.Boolean(
        default=True,
        string="Include Accessory Costs in Intrastat",
        help="In Sweden, accessory costs (freight, insurance) must be included "
        "in the statistical value for Intrastat reporting.",
    )

    @api.model
    def _intrastat_arrivals(self):
        """Extend base selection with Swedish-specific options."""
        return super()._intrastat_arrivals() + [
            ("standard_se", "Standard (≥ 12 MSEK)"),
            ("extended_se", "Extended (≥ 550 MSEK)"),
        ]

    @api.model
    def _intrastat_dispatches(self):
        """Extend base selection with Swedish-specific options."""
        return super()._intrastat_dispatches() + [
            ("standard_se", "Standard (≥ 5 MSEK)"),
            ("extended_se", "Extended (≥ 275 MSEK)"),
        ]

    intrastat_contact_name = fields.Char(
        string="Intrastat Contact Person",
        help="Contact person for SCB Intrastat enquiries.",
    )
    intrastat_contact_phone = fields.Char(
        string="Intrastat Contact Phone",
        help="Phone number for SCB Intrastat enquiries.",
    )
    intrastat_contact_email = fields.Char(
        string="Intrastat Contact Email",
        help="Email for SCB Intrastat enquiries.",
    )

    @api.model
    def _get_intrastat_arrivals_threshold(self):
        """Return Swedish arrivals threshold in company currency."""
        return SE_ARRIVALS_THRESHOLD

    @api.model
    def _get_intrastat_dispatches_threshold(self):
        """Return Swedish dispatches threshold in company currency."""
        return SE_DISPATCHES_THRESHOLD
