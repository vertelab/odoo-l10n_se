# Copyright 2026 Vertel AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class AccountPaymentMode(models.Model):
    _inherit = "account.payment.mode"

    se_initiating_party_identifier = fields.Char(
        string="SE Initiating Party Identifier",
        size=35,
        help="Swedish Bankgironummer or customer identifier used in the "
        "InitgPty/Id/OrgId/Othr/Id element. If left empty, the company-level "
        "value is used.",
    )
    se_initiating_party_scheme = fields.Selection(
        [("BANK", "BANK"), ("CUST", "CUST")],
        string="SE Initiating Party Scheme",
        default="BANK",
        help="Scheme name code for the initiating party identifier. "
        "BANK = Bank Party ID, CUST = Customer Number. "
        "Check with your bank which one to use.",
    )
    se_corporate_pay_agreement_id = fields.Char(
        string="SE Corporate Pay Agreement ID",
        size=35,
        help="Swedbank Corporate Pay Agreement ID used in "
        "Dbtr/Id/OrgId/Othr/Id. Format: nnnnnnnnnnAnnn (e.g. 123456789123B001). "
        "If left empty, the company-level value is used. "
        "Leave empty for ISO 1.0.",
    )
