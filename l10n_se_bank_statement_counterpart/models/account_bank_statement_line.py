# Copyright 2026 Vertel Sverige AB (<https://vertel.se>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import _, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    def _prepare_move_line_default_vals(self, counterpart_account_id=None):
        """Resolve the counterpart account when the journal forbids interim
        accounts.

        This covers two situations:

        * import, where the counterpart is already resolved by
          ``_statement_line_import_update_hook``;
        * ``action_undo_reconciliation``, which calls this method without an
          argument to rebuild the original journal items. In that case we
          resolve the counterpart ourselves instead of falling back to the
          suspense account.

        If the counterpart still cannot be determined we raise: a silent
        suspense posting is worse than a loud error, because nobody notices
        it until reconciliation.
        """
        journal = self.journal_id
        if journal.no_suspense_counterpart and not counterpart_account_id:
            counterpart_account_id = journal._get_no_suspense_counterpart(
                {"partner_id": self.partner_id.id}
            )
            if not counterpart_account_id:
                raise UserError(
                    _(
                        "Journal %(journal)s is configured to never use a "
                        "suspense account, but no counterpart account could be "
                        "determined for the bank statement line %(ref)s "
                        "(%(amount)s).\n\n"
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
