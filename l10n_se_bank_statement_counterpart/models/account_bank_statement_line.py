# Copyright 2026 Vertel Sverige AB (<https://vertel.se>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


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
        # Callers pass either an id or an account recordset; normalise to id so
        # the parent implementation and the ORM always see an integer.
        if isinstance(counterpart_account_id, models.BaseModel):
            counterpart_account_id = counterpart_account_id.id
        if journal.no_suspense_counterpart:
            # The reference is a stronger signal than the sign of the amount,
            # so resolve it even when the caller already supplied a
            # counterpart (the parent ``create()`` passes the journal default,
            # which is receivable-first and wrong for a vendor bill).
            resolved = journal._get_no_suspense_counterpart(
                {
                    "partner_id": self.partner_id.id,
                    "payment_ref": self.payment_ref,
                    "amount": self.amount,
                }
            )
            if resolved:
                counterpart_account_id = resolved
            # ``_get_no_suspense_counterpart`` returns an account recordset;
            # the parent implementation expects an id.
            if isinstance(counterpart_account_id, models.BaseModel):
                counterpart_account_id = counterpart_account_id.id
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
        if journal.no_suspense_counterpart and counterpart_account_id:
            account = self.env["account.account"].browse(counterpart_account_id)
            if journal._is_suspense_account(account):
                raise UserError(
                    _(
                        "Journal %(journal)s is configured to never use a "
                        "suspense account, but the counterpart resolved to "
                        "the interim account %(account)s for bank statement "
                        "line %(ref)s (%(amount)s).\n\n"
                        "Set a partner on the line, or configure a default "
                        "counterpart account on the journal.",
                        journal=journal.display_name,
                        account=account.display_name,
                        ref=self.payment_ref or _("(no reference)"),
                        amount=self.amount,
                    )
                )
        res = super()._prepare_move_line_default_vals(
            counterpart_account_id=counterpart_account_id
        )

        # NOTE: early-payment discount lines are added in ``create()``, not
        # here. The parent ``create()`` writes on the move before the journal
        # items exist, and any extra line returned from this method makes
        # ``_synchronize_from_moves`` see a move without a liquidity line.
        return res

    @api.model_create_multi
    def create(self, vals_list):
        """Add early-payment discount lines once the statement move exists.

        The parent ``create()`` builds the move's journal items from
        ``_prepare_move_line_default_vals`` and synchronises the statement
        line against them. Returning extra lines from that method breaks the
        synchronisation, because the move is written before the items exist.
        Adding them here lets the parent finish first and then top the entry
        up with the discount.
        """
        lines = super().create(vals_list)
        for line in lines:
            if not line.journal_id.no_suspense_counterpart:
                continue
            discount_vals = line._prepare_move_line_default_vals_with_discount()
            if not discount_vals:
                continue
            self._apply_early_payment_discount(line, discount_vals)
        return lines

    def _apply_early_payment_discount(self, st_line, discount_vals):
        """Book the discount lines and clear the payable in full."""
        move = st_line.move_id
        payable = move.line_ids.filtered(
            lambda ml: ml.account_id.account_type == "liability_payable"
        )
        if not payable:
            return
        for vals in discount_vals:
            balance = vals.pop("balance", 0.0)
            vals["debit"] = balance if balance > 0.0 else 0.0
            vals["credit"] = -balance if balance < 0.0 else 0.0
            vals.pop("amount_currency", None)
            vals["move_id"] = move.id
            vals.setdefault("partner_id", st_line.partner_id.id)
        discount_balance = sum(v["debit"] - v["credit"] for v in discount_vals)
        # The entry is already posted. The discount lines carry credit, so
        # the payable has to grow by the same amount to stay balanced; both
        # writes are made with move validation off so the entry is only
        # checked once it is complete.
        target = payable.balance - discount_balance
        ctx = {"check_move_validity": False, "skip_account_move_synchronization": True}
        payable.with_context(**ctx).write(
            {
                "debit": target if target > 0.0 else 0.0,
                "credit": -target if target < 0.0 else 0.0,
            }
        )
        self.env["account.move.line"].with_context(**ctx).create(discount_vals)
        move.line_ids.invalidate_recordset()

    def _prepare_move_line_default_vals_with_discount(self):
        """Return journal item values including the early-payment discount.

        Odoo books an early-payment discount as extra lines next to the
        invoice's own lines: the expense account is credited and the input
        VAT is reduced, so the payable is cleared in full while the bank only
        moves the discounted amount.

        Because this module books the counterpart on a real account instead
        of the suspense account, Odoo's reconciliation flow cannot add those
        lines afterwards. We therefore build them here, using Odoo's own
        helper so the amounts, tax tags and rounding match what the
        reconciliation widget would have produced.
        """
        journal = self.journal_id
        move = journal._get_discounted_move(
            {
                "payment_ref": self.payment_ref,
                "amount": self.amount,
                "partner_id": self.partner_id.id,
            }
        )
        if not move:
            return []

        term_lines = move.line_ids.filtered("discount_date")
        if not term_lines:
            return []

        # Only apply the discount when the payment date falls inside the
        # discount window; after that date the full amount is due.
        today = self.date or fields.Date.context_today(self)
        eligible = term_lines.filtered(
            lambda line: line.discount_date and today <= line.discount_date
        )
        if not eligible:
            return []

        aml_values_list = []
        for aml in eligible:
            aml_values_list.append(
                {
                    "aml": aml,
                    "amount_currency": -aml.amount_residual_currency,
                    "balance": aml.currency_id._convert(
                        -aml.amount_residual_currency,
                        aml.company_currency_id,
                        self.company_id,
                        today,
                    ),
                }
            )

        # ``open_balance`` is the part of the payable that the discount lines
        # have to cover: what the invoice still owes minus what the bank
        # actually moved.
        # ``amount_residual`` is negative on a payable (credit). The bank
        # moved ``self.amount`` of it, so what remains to be covered by the
        # discount is the residual plus the payment.
        open_balance = sum(eligible.mapped("amount_residual")) + abs(self.amount)
        early_payment_values = self.env[
            "account.move"
        ]._get_invoice_counterpart_amls_for_early_payment_discount(
            aml_values_list, open_balance
        )

        line_vals = []
        for aml_values in early_payment_values.values():
            for vals in aml_values:
                vals.setdefault("move_id", self.move_id.id)
                vals.setdefault("partner_id", self.partner_id.id)
                line_vals.append(vals)
        return line_vals
