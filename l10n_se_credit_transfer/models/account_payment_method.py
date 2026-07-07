# Copyright 2026 Vertel AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class AccountPaymentMethod(models.Model):
    _inherit = "account.payment.method"

    pain_version = fields.Selection(
        selection_add=[
            ("pain.001.001.03", "pain.001.001.03"),
            ("pain.001.001.09", "pain.001.001.09"),
        ],
        ondelete={
            "pain.001.001.03": "set null",
            "pain.001.001.09": "set null",
        },
    )

    se_org_id_required = fields.Boolean(
        string="Org ID Required",
        default=True,
        help="When enabled, the Initiating Party Identifier must be set "
        "on the Payment Mode or Company before a payment file can be "
        "generated. Disable only if your bank does not require an "
        "organisation ID.",
    )

    def get_xsd_file_path(self):
        self.ensure_one()
        if self.pain_version in ("pain.001.001.03", "pain.001.001.09"):
            return f"l10n_se_credit_transfer/data/{self.pain_version}.xsd"
        return super().get_xsd_file_path()

    @api.model
    def _get_payment_method_information(self):
        res = super()._get_payment_method_information()
        for code in ("se_credit_transfer", "se_credit_transfer_20", "bankgiro"):
            res[code] = {
                "mode": "multi",
                "domain": [("type", "=", "bank")],
            }
        res["autogiro"] = {
            "mode": "multi",
            "type": ("bank", "cash", "credit"),
        }
        return res
