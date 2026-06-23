# Copyright 2026 Vertel AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    se_initiating_party_identifier = fields.Char(
        string="SE Initiating Party Identifier",
        size=35,
        help="Swedish Bankgironummer or customer identifier used in the "
        "InitgPty/Id/OrgId/Othr/Id element of the ISO 20022 XML file.",
    )
    se_initiating_party_scheme = fields.Selection(
        [("BANK", "BANK"), ("CUST", "CUST")],
        string="SE Initiating Party Scheme",
        default="BANK",
        help="Scheme name code for the initiating party identifier. "
        "BANK = Bank Party ID, CUST = Customer Number.",
    )
