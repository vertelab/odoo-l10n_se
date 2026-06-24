# Copyright 2026 Vertel AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class AccountPaymentMode(models.Model):
    _inherit = "account.payment.mode"

    se_initiating_party_identifier = fields.Char(
        string="SE Initiating Party Identifier",
        size=35,
        help="Identifier sent in the InitgPty/Id/OrgId/Othr/Id element.\n"
        "For Swedbank MIG 2.0: signer ID with format nnnnnnnnnORInnnn "
        "(e.g. 012345678ORI0001).\n"
        "For other banks: your Bankgironummer or customer number.\n"
        "Leave empty to use the company-level value.",
    )
    se_corporate_pay_agreement_id = fields.Char(
        string="SE Corporate Pay Agreement ID",
        size=35,
        help="Corporate Pay Agreement ID for Dbtr/Id/OrgId/Othr/Id.\n"
        "For Swedbank MIG 2.0: format nnnnnnnnnCPOnnnn "
        "(e.g. 123456789CPO0001) — get this from your Swedbank agreement.\n"
        "Leave empty to use the company-level value.",
    )
