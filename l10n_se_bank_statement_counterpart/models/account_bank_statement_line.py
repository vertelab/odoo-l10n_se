# Copyright 2026 Vertel Sverige AB (<https://vertel.se>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import _, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    def _prepare_move_line_default_vals(self, counterpart_account_id=None):
        """Refuse to book against the suspense account when the journal
        forbids interim accounts.

        This is the last line of defence: if the counterpart could not be
        resolved during import, we raise instead of silently parking the
        amount on an interim account. A silent suspense posting is worse
        than a loud error, because nobody notices it until reconciliation.
        """
        journal = self.journal_id
        if journal.no_suspense_counterpart and not counterpart_account_id:
            raise UserError(
                _(
                    "Journal %(journal)s is configured to never use a suspense "
                    "account, but no counterpart account could be determined "
                    "for the bank statement line %(ref)s (%(amount)s).\n\n"
                    "Set a partner on the line, or configure a default "
                    "counterpart account on the journal.",
                    journal=journal.display_name,
                    ref=self.payment_ref or _("(no reference)"),
                    amount=self.amount,
                )
            )
        return super()._prepare_move_line_default_vals(
            counterpart_account_id=counterpart_account_id
        )

    def _seek_for_lines(self):
        """Treat the configured counterpart account as the suspense line.

        Odoo's ``_compute_is_reconciled`` looks for a line on
        ``journal.suspense_account_id`` to decide whether a statement line
        still has an unreconciled counterpart::

            if suspense_lines:
                is_reconciled = is_zero(amount_residual)
            else:
                is_reconciled = True          # <-- assumes "already reconciled"

        When this module books the counterpart directly on a real account
        (1510/2440), that line lands in ``other_lines`` instead, the
        ``suspense_lines`` recordset is empty, and Odoo marks the line as
        reconciled before anyone has reconciled anything. The line then
        disappears from the reconciliation widget.

        Returning the counterpart line as the suspense line keeps Odoo's
        reconciliation state machine intact while still booking the amount
        on a real account.
        """
        liquidity_lines, suspense_lines, other_lines = super()._seek_for_lines()
        if suspense_lines or not self.journal_id.no_suspense_counterpart:
            return liquidity_lines, suspense_lines, other_lines

        counterpart_accounts = self.journal_id._no_suspense_counterpart_accounts()
        if not counterpart_accounts:
            return liquidity_lines, suspense_lines, other_lines

        counterpart_lines = other_lines.filtered(
            lambda line: line.account_id in counterpart_accounts
        )
        if not counterpart_lines:
            return liquidity_lines, suspense_lines, other_lines

        return (
            liquidity_lines,
            counterpart_lines,
            other_lines - counterpart_lines,
        )
