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
            # Already resolved by another module - respect it, but make sure
            # it is not an interim account.
            if self._is_suspense_account(
                self.env["account.account"].browse(
                    st_line_vals["counterpart_account_id"]
                )
            ):
                _logger.warning(
                    "Journal %s: another module set the interim account %s as "
                    "counterpart for statement line %r. Replacing it with a "
                    "real counterpart account.",
                    self.display_name,
                    st_line_vals["counterpart_account_id"],
                    st_line_vals.get("payment_ref"),
                )
                st_line_vals.pop("counterpart_account_id")
            else:
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

        1. The open invoice matched by the payment reference. A reference
           such as ``BILL/2026/11/0007`` identifies the document being paid,
           which is a far stronger signal than the sign of the amount: it
           tells us whether this is a vendor bill (payable) or a customer
           invoice (receivable) regardless of how the bank encoded the
           amount.
        2. The partner's own property account (receivable for incoming,
           payable for outgoing).
        3. The journal's configured receivable/payable counterpart.

        Returns ``False`` when the referenced document offers an
        early-payment discount: Odoo's reconciliation must book that discount
        itself, and a pre-booked counterpart makes the resulting entry
        unbalanced.

        ``speeddict`` is only available during import; when called from
        ``action_undo_reconciliation`` it is omitted and the partner is
        taken from ``st_line_vals['partner_id']`` alone.
        """
        amount = st_line_vals.get("amount") or 0.0
        incoming = amount >= 0

        # 1. Resolve from the document referenced by the payment reference.
        #    This is what makes a vendor bill imported with a positive amount
        #    land on 2440 instead of 1510.
        document_account = self._get_counterpart_from_reference(st_line_vals)
        if document_account:
            return document_account

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
            if account and not self._is_suspense_account(account):
                return account

        fallback = (
            self.counterpart_receivable_account_id
            if incoming
            else self.counterpart_payable_account_id
        )
        if fallback and not self._is_suspense_account(fallback):
            return fallback
        return False

    def _get_discounted_move(self, st_line_vals):
        """Return the invoice/bill referenced by the line when it carries an
        early-payment discount, else an empty recordset.

        Odoo books the discount itself during reconciliation: it credits the
        expense account and reduces the input VAT, and the resulting entry is
        only balanced if the statement line is still unreconciled. Pre-booking
        a counterpart account on the line makes Odoo refuse the reconciliation
        with "The entry is not balanced".

        So when the referenced document offers an early-payment discount we
        deliberately leave the counterpart unresolved, letting Odoo's own
        reconciliation flow do the work.
        """
        reference = (st_line_vals.get("payment_ref") or "").strip()
        if not reference:
            return self.env["account.move"]

        move_model = self.env["account.move"]
        for token in self._reference_tokens(reference):
            if not self._is_document_number(token):
                continue
            moves = move_model.search(
                [
                    ("name", "=", token),
                    ("state", "=", "posted"),
                    (
                        "move_type",
                        "in",
                        ("in_invoice", "in_refund", "out_invoice", "out_refund"),
                    ),
                ],
                limit=2,
            )
            if len(moves) != 1:
                continue
            if not self._reference_matches_move(st_line_vals, moves):
                continue
            if moves.line_ids.filtered("discount_date"):
                return moves
        return move_model

    def _get_counterpart_from_reference(self, st_line_vals):
        """Return the counterpart account implied by the payment reference.

        Looks for a posted invoice or bill whose number appears in the
        statement line's reference, and returns the account the document's
        outstanding line sits on (payable for a vendor bill, receivable for a
        customer invoice).

        The match is validated against the partner and the amount when those
        are available, so a coincidental number match cannot redirect the
        posting to an unrelated account.

        Returns ``None`` when no document matches, so the caller falls back to
        the sign-based resolution.
        """
        reference = (st_line_vals.get("payment_ref") or "").strip()
        if not reference:
            return False

        move_model = self.env["account.move"]
        for token in self._reference_tokens(reference):
            if not self._is_document_number(token):
                continue
            moves = move_model.search(
                [
                    ("name", "=", token),
                    ("state", "=", "posted"),
                    (
                        "move_type",
                        "in",
                        ("in_invoice", "in_refund", "out_invoice", "out_refund"),
                    ),
                ],
                limit=2,
            )
            if len(moves) != 1:
                # No match, or an ambiguous match we refuse to guess about.
                continue
            move = moves
            if not self._reference_matches_move(st_line_vals, move):
                _logger.info(
                    "Statement line %r references %s but the partner or amount "
                    "does not match; ignoring the reference.",
                    reference,
                    move.name,
                )
                continue
            if move.move_type in ("in_invoice", "in_refund"):
                account = move.partner_id.property_account_payable_id
            else:
                account = move.partner_id.property_account_receivable_id
            if account and not self._is_suspense_account(account):
                return account
        return False

    @api.model
    def _reference_matches_move(self, st_line_vals, move):
        """Return True when the statement line plausibly pays *move*.

        Guards against a coincidental number match. We only reject when the
        evidence is clear: a different partner, or an amount that is larger
        than the document's outstanding balance. Missing data never rejects.
        """
        partner_id = st_line_vals.get("partner_id")
        if partner_id and move.partner_id and partner_id != move.partner_id.id:
            return False

        amount = st_line_vals.get("amount")
        if amount is None:
            return True
        amount = abs(amount)
        residual = abs(move.amount_residual)
        if not residual:
            # Fully paid already; still a valid reference for the account.
            return True
        # Allow a small tolerance for currency rounding and early-payment
        # discounts, but reject an amount that clearly belongs elsewhere.
        if amount > residual * 1.5 + 1.0:
            return False
        return True

    @api.model
    def _is_document_number(self, token):
        """Return True when *token* looks like an Odoo document number.

        Odoo numbers look like ``BILL/2026/11/0007`` or ``INV/2026/00869``.
        Requiring a separator keeps short numeric bank references from
        matching unrelated documents by accident.
        """
        if not token or len(token) < 5:
            return False
        return "/" in token or "-" in token

    @api.model
    def _reference_tokens(self, reference):
        """Split a bank reference into candidate document numbers.

        Banks prefix the reference with free text (``"BILL/2026/11/0007"``,
        ``"Betalning BILL/2026/11/0007"``). We return the whole reference
        first, then every whitespace-separated token, so an exact document
        number always wins over a partial one.
        """
        tokens = [reference]
        tokens.extend(part for part in reference.split() if part != reference)
        return tokens

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
        """Return True when *account* is an interim/suspense account.

        Detection is by account type and by name, and covers the Swedish and
        English names used in practice. Odoo's own interim accounts are
        ``asset_current``/``liability_current``; a real receivable or payable
        account is never interim, so those types short-circuit to False.
        """
        if not account:
            return False
        if account.account_type in ("asset_receivable", "liability_payable"):
            return False
        if account.account_type not in ("asset_current", "liability_current"):
            return False

        name = (account.name or "").lower()
        markers = (
            "suspense",
            "transit",
            "interim",
            "outstanding",
            "avstäm",
            "väntkonto",
            "mellankonto",
        )
        return any(marker in name for marker in markers)

    def _no_suspense_counterpart_accounts(self):
        """Return the accounts this journal may use as counterpart.

        Used by ``account.bank.statement.line._seek_for_lines()`` to keep
        Odoo's reconciliation state machine working when the counterpart is
        booked on a real account instead of the suspense account.

        The configured accounts are included, but so is every real
        receivable/payable account: the reference-based resolution may pick a
        partner-specific account (2441 Utländska leverantörsskulder, 2460
        koncerninterna skulder, a customer-specific receivable) which is not
        one of the two configured defaults. Without those, Odoo would treat
        the line as already reconciled and hide it from the reconciliation
        widget.
        """
        self.ensure_one()
        configured = (
            self.counterpart_receivable_account_id
            | self.counterpart_payable_account_id
        )
        real_accounts = self.env["account.account"].search(
            [("account_type", "in", ("asset_receivable", "liability_payable"))]
        )
        return configured | real_accounts
