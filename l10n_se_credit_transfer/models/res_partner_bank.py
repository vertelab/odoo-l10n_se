# Copyright 2026 Vertel AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


def normalize_bgnr(bgnr):
    return re.sub("[^0-9]", "", bgnr or "")


def check_luhn(s):
    return (
        sum(
            map(
                lambda x: x % 10 + int(x / 10),
                map(lambda x, y: x * y, map(int, s), [2, 1] * 5),
            )
        )
        % 10
        == 0
    )


def validate_bgnr(bgnr):
    if not bgnr:
        raise ValidationError(_("There is no Bankgiro Number."))

    if bgnr.find("-") not in range(3, 5):
        raise ValidationError(
            _("There is no dash in position 3 or 4 in the Number.")
        )

    bgnr = normalize_bgnr(bgnr)

    if len(bgnr) not in range(7, 9):
        raise ValidationError(
            _(
                "A bankgiro number can only consist of 7 or 8 digits and one dash."
            )
        )

    if not check_luhn(f"{int(bgnr):08d}"):
        raise ValidationError(
            _("The bankgiro number is not valid the checksum is not correct.")
        )


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    acc_type = fields.Selection(
        selection=lambda x: x.env["res.partner.bank"]._get_supported_account_types(),
        compute="_compute_acc_type",
        string="Type",
        store=True,
        help="Bank account type: IBAN, BGNR or Normal. Inferred from the account number.",
    )

    @api.model
    def _get_supported_account_types(self):
        """Add new account type named bgnr (BankGiro) used in Sweden"""
        rslt = super()._get_supported_account_types()
        rslt.append(("bgnr", _("BGNR")))
        return rslt

    @api.model
    def retrieve_acc_type(self, acc_number):
        try:
            validate_bgnr(acc_number)
            return "bgnr"
        except Exception:
            return super().retrieve_acc_type(acc_number)
