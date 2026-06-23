# Copyright 2026 Vertel AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class AccountPaymentLine(models.Model):
    _inherit = "account.payment.line"

    se_end_to_end_id = fields.Char(
        string="End-to-End ID (SE)",
        size=35,
        help="Unique end-to-end identifier for Swedish payments. "
        "Leave empty to auto-generate.",
    )
