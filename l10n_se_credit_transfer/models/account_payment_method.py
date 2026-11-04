# Copyright 2026 Vertel Sverige AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

# Payment methods whose file generation lives in this module — the ones that
# must be reachable from an account.payment.mode.
SE_PAYMENT_METHOD_CODES = (
    "se_credit_transfer",
    "se_credit_transfer_20",
)


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
        for code in ("se_credit_transfer", "se_credit_transfer_20"):
            res[code] = {
                "mode": "multi",
                "domain": [("type", "=", "bank")],
            }
        res["autogiro"] = {
            "mode": "multi",
            "type": ("bank", "cash", "credit"),
        }
        return res


class AccountPaymentMode(models.Model):
    _inherit = "account.payment.mode"

    def unlink(self):
        """Refuse to remove the last mode of an active Swedish method."""
        self._check_se_payment_mode_linked()
        return super().unlink()

    @api.model_create_multi
    def create(self, vals_list):
        """Let the first mode of a method be created without a guard trip."""
        modes = super(
            AccountPaymentMode, self.with_context(se_payment_mode_setup=True)
        ).create(vals_list)
        modes._check_se_payment_mode_linked()
        return modes

    @api.constrains("payment_method_id")
    def _check_se_payment_mode_linked(self):
        """A Swedish (ISO 20022) payment method must be reachable from a mode.

        The payment method alone cannot produce a payment order: the order is
        created from an ``account.payment.mode``, and the SE generator reads
        the signer ID and Corporate Pay Agreement ID from that mode. A method
        without a mode is therefore dead configuration — the user sees the
        method in the journal but can never build an order from it.
        """
        modes = self.env["account.payment.mode"].sudo()
        for mode in self:
            method = mode.payment_method_id
            if method.code not in SE_PAYMENT_METHOD_CODES:
                continue
            if method.payment_type != "outbound" or not method.active:
                continue
            if self.env.context.get("se_payment_mode_setup"):
                continue
            others = modes.search_count(
                [
                    ("payment_method_id", "=", method.id),
                    ("id", "not in", mode._origin.ids or [0]),
                ]
            )
            if not others:
                raise ValidationError(
                    _(
                        "The payment method '%(method)s' would be left without "
                        "a payment mode. Keep at least one mode for it — "
                        "otherwise no payment order can be created with this "
                        "method.",
                        method=method.name,
                    )
                )
