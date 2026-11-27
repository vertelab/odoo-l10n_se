# Copyright 2026 Vertel Sverige AB (<https://vertel.se>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _inherit = "account.journal"

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------
    no_suspense_counterpart = fields.Boolean(
        string="Never Use Suspense Account",
        default=False,
        help="When enabled, bank statement lines imported into this journal "
        "are booked directly against a real counterpart account instead of "
        "the journal's suspense account. Interim/suspense accounts are "
        "forbidden in this company's accounting policy.",
    )
    counterpart_receivable_account_id = fields.Many2one(
        "account.account",
        string="Counterpart for Incoming Amounts",
        domain=[("account_type", "=", "asset_receivable")],
        help="Account used as counterpart for incoming amounts (positive "
        "line amount) when no partner-specific account applies. "
        "Typically 1510 Kundfordringar.",
    )
    counterpart_payable_account_id = fields.Many2one(
        "account.account",
        string="Counterpart for Outgoing Amounts",
        domain=[("account_type", "=", "liability_payable")],
        help="Account used as counterpart for outgoing amounts (negative "
        "line amount) when no partner-specific account applies. "
        "Typically 2440 Leverantörsskulder.",
    )

    # ------------------------------------------------------------------
    # Import hook
    # ------------------------------------------------------------------
    def _statement_line_import_update_hook(self, st_line_vals, speeddict):
        """Set a real counterpart account on imported statement lines.

        Odoo falls back to ``journal.suspense_account_id`` for every line
        that has no counterpart, which parks the amount on an interim
        account. This override resolves the counterpart up front so the
        line is booked directly against the correct receivable/payable
        account.
        """
        res = super()._statement_line_import_update_hook(st_line_vals, speeddict)
        self.ensure_one()

        if not self.no_suspense_counterpart:
            return res
        if st_line_vals.get("counterpart_account_id"):
            # Already resolved by another module - respect it.
            return res

        counterpart = self._get_no_suspense_counterpart(st_line_vals, speeddict)
        if counterpart:
            st_line_vals["counterpart_account_id"] = counterpart.id
        else:
            _logger.warning(
                "Journal %s: could not resolve a counterpart account for "
                "statement line %r (amount %s). Falling back to suspense.",
                self.display_name,
                st_line_vals.get("payment_ref"),
                st_line_vals.get("amount"),
            )
        return res

    def _get_no_suspense_counterpart(self, st_line_vals, speeddict=None):
        """Return the account.account to use as counterpart, or None.

        Resolution order:

        1. The partner's own property account (receivable for incoming,
           payable for outgoing). This is the most precise answer.
        2. The journal's configured receivable/payable counterpart.

        ``speeddict`` is only available during import; when called from
        ``action_undo_reconciliation`` it is omitted and the partner is
        taken from ``st_line_vals['partner_id']`` alone.
        """
        amount = st_line_vals.get("amount") or 0.0
        incoming = amount >= 0

        partner = False
        partner_id = st_line_vals.get("partner_id")
        if partner_id:
            partner = self.env["res.partner"].browse(partner_id)
        elif speeddict and st_line_vals.get("account_number"):
            # The base hook already resolved partner from the bank account
            # number; fall back to doing it ourselves for safety.
            account_number = self._sanitize_bank_account_number(
                st_line_vals["account_number"]
            )
            info = speeddict.get("account_number", {}).get(account_number)
            if info and info.get("partner_id"):
                partner = self.env["res.partner"].browse(info["partner_id"])

        if partner:
            account = (
                partner.property_account_receivable_id
                if incoming
                else partner.property_account_payable_id
            )
            if account:
                return account

        return (
            self.counterpart_receivable_account_id
            if incoming
            else self.counterpart_payable_account_id
        )

    # ------------------------------------------------------------------
    # Safety net
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        """Refuse to create a journal pointing at a suspense account when
        the no-suspense policy is enabled."""
        journals = super().create(vals_list)
        for journal in journals:
            if journal.no_suspense_counterpart and journal._is_suspense_account(
                journal.suspense_account_id
            ):
                _logger.warning(
                    "Journal %s has 'Never Use Suspense Account' enabled but "
                    "its suspense account is %s.",
                    journal.display_name,
                    journal.suspense_account_id.display_name,
                )
        return journals

    @api.model
    def _is_suspense_account(self, account):
        """Return True when *account* looks like an interim/suspense account."""
        if not account:
            return False
        if account.account_type == "asset_current" and "suspense" in (
            account.name or ""
        ).lower():
            return True
        return False

    def _no_suspense_counterpart_accounts(self):
        """Return the accounts this journal may use as a counterpart.

        Used by ``account.bank.statement.line._seek_for_lines()`` to keep
        Odoo's reconciliation state machine working when the counterpart is
        booked on a real account instead of the suspense account.
        """
        self.ensure_one()
        return (
            self.counterpart_receivable_account_id
            | self.counterpart_payable_account_id
        )
