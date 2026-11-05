from dateutil.relativedelta import relativedelta
from odoo.modules.registry import Registry
from odoo.exceptions import RedirectWarning
from odoo import models, fields, api, _
from odoo import http
from odoo.http import request
from odoo import tools

import random

import logging

_logger = logging.getLogger(__name__)

from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from datetime import timedelta, date, datetime

import odoo.addons.decimal_precision as dp


# ~ This adds a default credit/debit account field for the account journal, since the fields loss/profit_account_id
# seems to have specific purposes that i don't understand
class account_journal(models.Model):
    _inherit = 'account.journal'

    default_credit_account_id = fields.Many2one(comodel_name='account.account', check_company=True, copy=False,
                                                ondelete='restrict', string='Default Credit Account',
                                                domain=[('deprecated', '=', False)],
                                                )

    default_debit_account_id = fields.Many2one(comodel_name='account.account', check_company=True, copy=False,
                                               ondelete='restrict', string='Default Debit Account',
                                               domain=[('deprecated', '=', False)],
                                               )

    @api.onchange('default_debit_account_id')
    def onchange_debit_account_id(self):
        if not self.default_credit_account_id:
            self.default_credit_account_id = self.default_debit_account_id

    @api.onchange('default_credit_account_id')
    def onchange_credit_account_id(self):
        if not self.default_debit_account_id:
            self.default_debit_account_id = self.default_credit_account_id

    # ------------------------------------------------------------------
    # Tax account (1630) as bank counterpart
    # ------------------------------------------------------------------
    TAX_ACCOUNT_CODE = "1630"

    def _l10n_se_tax_report_get_tax_account(self):
        """Return the tax account (1630) for this journal's company."""
        self.ensure_one()
        return self.env["account.account"].search(
            [
                ("company_ids", "in", [self.company_id.id]),
                ("code", "=", self.TAX_ACCOUNT_CODE),
            ],
            limit=1,
        )

    def _l10n_se_tax_report_is_skatteverket_line(self, st_line_vals, speeddict=None):
        """True when a bank statement line settles the Swedish Tax Agency.

        Two signals are accepted, in order of strength:

        1. The partner resolved for the line is the Skatteverket partner
           created by this module.
        2. The payment reference mentions a tax payment. This catches lines
           imported without a partner match, where the bank text still says
           what the payment is for.
        """
        self.ensure_one()
        skv_partner = self.env.ref(
            "l10n_se_tax_report.res_partner-SKV", raise_if_not_found=False
        )
        if not skv_partner:
            return False

        partner_id = st_line_vals.get("partner_id")
        if partner_id and partner_id == skv_partner.id:
            return True

        # The base import hook resolves the partner from the bank account
        # number; check that too when it is available.
        if speeddict and st_line_vals.get("account_number"):
            account_number = self._sanitize_bank_account_number(
                st_line_vals["account_number"]
            )
            info = speeddict.get("account_number", {}).get(account_number)
            if info and info.get("partner_id") == skv_partner.id:
                return True

        reference = " ".join(
            str(st_line_vals.get(key) or "")
            for key in ("payment_ref", "ref", "narration")
        ).lower()
        if not reference:
            return False
        keywords = ("skatteverket", "skattekonto", "moms", "f-skatt", "arbetsgivaravgift")
        return any(keyword in reference for keyword in keywords)

    def _get_no_suspense_counterpart(self, st_line_vals, speeddict=None):
        """Book tax payments straight against the tax account (1630).

        The VAT declaration moves the net VAT from 2650 to 1630
        (``mis_report_generator._create_tax_account_transfer``). For the
        payment to reconcile against that entry, the bank statement line
        must carry 1630 as its counterpart instead of the partner's generic
        payable account (2440).

        This override only applies when the journal has opted into
        ``no_suspense_counterpart``; journals that still use the suspense
        account keep their existing behaviour.
        """
        res = super()._get_no_suspense_counterpart(st_line_vals, speeddict)
        self.ensure_one()

        if not self.no_suspense_counterpart:
            return res
        if not self._l10n_se_tax_report_is_skatteverket_line(st_line_vals, speeddict):
            return res

        tax_account = self._l10n_se_tax_report_get_tax_account()
        if not tax_account:
            _logger.warning(
                "Journal %s: tax account %s not found, keeping counterpart %s "
                "for statement line %r.",
                self.display_name,
                self.TAX_ACCOUNT_CODE,
                res.code if res else None,
                st_line_vals.get("payment_ref"),
            )
            return res

        return tax_account
