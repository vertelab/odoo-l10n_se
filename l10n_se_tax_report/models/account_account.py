# Copyright 2026 Vertel Sverige AB (<https://vertel.se>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, models
from odoo.exceptions import UserError

# BAS account 1630 "Avräkning för skatter och avgifter (skattekonto)".
# The VAT declaration moves the net VAT from 2650 to this account
# (see mis_report_generator._create_tax_account_transfer). For the payment
# to be reconcilable against the declaration, the account must be marked
# as reconcilable and must be reachable from the bank journal as a
# counterpart.
TAX_ACCOUNT_CODE = "1630"

# BAS account 2650 "Redovisningskonto för moms". The VAT report books the
# net VAT here, and the amount stays until the declaration is confirmed and
# the transfer to 1630 is created. While it sits on 2650 it must be
# reconcilable, otherwise it is invisible to the bank reconciliation widget
# (account.bank.statement.line._get_default_amls_matching_domain filters on
# account.account.reconcile).
VAT_ACCOUNT_CODE = "2650"


class AccountAccount(models.Model):
    _inherit = "account.account"

    def _l10n_se_tax_report_is_tax_account(self):
        """True when this account is the Swedish tax account (1630)."""
        self.ensure_one()
        return self.code == TAX_ACCOUNT_CODE

    def _l10n_se_tax_report_configure_tax_account(self):
        """Make 1630 and 2650 reconcilable.

        Called from the post-install hook and from the settings button so
        both fresh and upgraded databases get the same behaviour.

        1630 must be reconcilable so the Skatteverket payment can be matched
        against the declaration transfer. 2650 must be reconcilable so the
        VAT debt is visible in the bank reconciliation while it is still
        waiting to be moved to 1630 - without it the amount could not be
        matched anywhere, because 2650 was excluded from the candidate list.

        Nothing is written when an account is missing or already correct,
        which keeps the method idempotent.
        """
        accounts = self.search([("code", "=", TAX_ACCOUNT_CODE)])
        if not accounts:
            raise UserError(
                _(
                    "The tax account %(code)s (Avräkning för skatter och "
                    "avgifter) was not found. Install the Swedish chart of "
                    "accounts before configuring the tax account.",
                    code=TAX_ACCOUNT_CODE,
                )
            )
        accounts.filtered(lambda a: not a.reconcile).write({"reconcile": True})

        # 2650 is optional: some charts rename it. Only touch it when present.
        vat_accounts = self.search([("code", "=", VAT_ACCOUNT_CODE)])
        vat_accounts.filtered(lambda a: not a.reconcile).write({"reconcile": True})

        return accounts | vat_accounts
