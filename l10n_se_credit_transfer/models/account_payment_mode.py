# Copyright 2026 Vertel AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class AccountPaymentMode(models.Model):
    _inherit = "account.payment.mode"

    se_initiating_party_identifier = fields.Char(
        string="SE Initiating Party Identifier",
        size=35,
        help="Identifier sent in the InitgPty/Id/OrgId/Othr/Id element.\n"
        "For Swedbank: signer ID with format nnnnnnnnnORInnnn "
        "(e.g. 012345678ORI0001).\n"
        "For other banks: your Bankgironummer or customer number.\n"
        "Leave empty to use the company-level value.",
    )
    se_initiating_party_scheme = fields.Selection(
        [("BANK", "BANK"), ("CUST", "CUST")],
        string="SE Initiating Party Scheme",
        default="BANK",
        help="Scheme code for the initiating party identifier.\n"
        "BANK = Bank Party ID (use for Swedbank, Handelsbanken, SEB).\n"
        "CUST = Customer Number (use for Nordea).\n"
        "Leave empty to use the company-level value.",
    )
    se_corporate_pay_agreement_id = fields.Char(
        string="SE Corporate Pay Agreement ID",
        size=35,
        help="Swedbank Corporate Pay Agreement ID for Dbtr/Id/OrgId/Othr/Id.\n"
        "Format: nnnnnnnnnnnnAnnn (e.g. 123456789123B001).\n"
        "Required by Swedbank MIG 2.0 only. "
        "Leave empty to use the company-level value.",
    )
