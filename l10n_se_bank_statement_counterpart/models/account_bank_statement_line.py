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
