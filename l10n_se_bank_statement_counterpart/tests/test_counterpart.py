# Copyright 2026 Vertel Sverige AB (<https://vertel.se>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBankStatementCounterpart(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.journal = cls.env["account.journal"].search(
            [("type", "=", "bank")], limit=1
        )
        if not cls.journal:
            cls.journal = cls.env["account.journal"].create(
                {"name": "Test Bank", "type": "bank", "code": "TBNK"}
            )
        cls.receivable = cls.env["account.account"].search(
            [("account_type", "=", "asset_receivable")], limit=1
        )
        cls.payable = cls.env["account.account"].search(
            [("account_type", "=", "liability_payable")], limit=1
        )
        cls.journal.write(
            {
                "no_suspense_counterpart": True,
                "counterpart_receivable_account_id": cls.receivable.id,
                "counterpart_payable_account_id": cls.payable.id,
            }
        )
        # Early-payment discounts need a discount account. Which one is a
        # bookkeeping decision made by the company (SFA books it on 3738), so
        # only supply one when the company has none configured.
        if not cls.env.company.account_journal_early_pay_discount_gain_account_id:
            cls.discount_account = cls.env["account.account"].create(
                {
                    "name": "Test Cash Discount",
                    "code": "T9991",
                    "account_type": "expense",
                    "company_ids": [(6, 0, cls.env.company.ids)],
                }
            )
            cls.env.company.write(
                {
                    "account_journal_early_pay_discount_loss_account_id": cls.discount_account.id,
                    "account_journal_early_pay_discount_gain_account_id": cls.discount_account.id,
                }
            )

    def _make_statement(self, balance_end):
        return self.env["account.bank.statement"].create(
            {
                "name": "TEST",
                "journal_id": self.journal.id,
                "balance_start": 0.0,
                "balance_end_real": balance_end,
            }
        )

    def _counterpart_accounts(self, line):
        return line.move_id.line_ids.filtered(
            lambda ml: ml.account_id != self.journal.default_account_id
        ).account_id

    def test_incoming_uses_receivable(self):
        """An incoming amount without a partner falls back to the journal's
        configured receivable counterpart, never to suspense."""
        statement = self._make_statement(100.0)
        line = self.env["account.bank.statement.line"].create(
            {
                "statement_id": statement.id,
                "journal_id": self.journal.id,
                "payment_ref": "Incoming",
                "amount": 100.0,
                "counterpart_account_id": self.receivable.id,
            }
        )
        self.assertEqual(self._counterpart_accounts(line), self.receivable)
        self.assertNotIn(
            self.journal.suspense_account_id, line.move_id.line_ids.account_id
        )

    def test_outgoing_uses_payable(self):
        """An outgoing amount without a partner falls back to the journal's
        configured payable counterpart, never to suspense."""
        statement = self._make_statement(-100.0)
        line = self.env["account.bank.statement.line"].create(
            {
                "statement_id": statement.id,
                "journal_id": self.journal.id,
                "payment_ref": "Outgoing",
                "amount": -100.0,
                "counterpart_account_id": self.payable.id,
            }
        )
        self.assertEqual(self._counterpart_accounts(line), self.payable)
        self.assertNotIn(
            self.journal.suspense_account_id, line.move_id.line_ids.account_id
        )

    def test_refuses_suspense_when_unresolved(self):
        """Without any counterpart the line must be refused, not silently
        parked on the suspense account."""
        self.journal.write(
            {
                "counterpart_receivable_account_id": False,
                "counterpart_payable_account_id": False,
            }
        )
        statement = self._make_statement(50.0)
        with self.assertRaises(UserError):
            self.env["account.bank.statement.line"].create(
                {
                    "statement_id": statement.id,
                    "journal_id": self.journal.id,
                    "payment_ref": "No counterpart",
                    "amount": 50.0,
                }
            )

    def test_suspense_allowed_when_policy_disabled(self):
        """Journals without the policy keep the standard Odoo behaviour."""
        self.journal.no_suspense_counterpart = False
        statement = self._make_statement(50.0)
        line = self.env["account.bank.statement.line"].create(
            {
                "statement_id": statement.id,
                "journal_id": self.journal.id,
                "payment_ref": "No counterpart",
                "amount": 50.0,
            }
        )
        self.assertIn(
            self.journal.suspense_account_id, line.move_id.line_ids.account_id
        )

    def test_hook_sets_counterpart_from_amount_sign(self):
        """The import hook resolves receivable for incoming amounts."""
        speeddict = {"account_number": {}}
        st_line_vals = {"amount": 250.0, "payment_ref": "Import test"}
        self.journal._statement_line_import_update_hook(st_line_vals, speeddict)
        self.assertEqual(
            st_line_vals.get("counterpart_account_id"), self.receivable.id
        )

    def test_hook_sets_counterpart_for_outgoing(self):
        """The import hook resolves payable for outgoing amounts."""
        speeddict = {"account_number": {}}
        st_line_vals = {"amount": -250.0, "payment_ref": "Import test"}
        self.journal._statement_line_import_update_hook(st_line_vals, speeddict)
        self.assertEqual(st_line_vals.get("counterpart_account_id"), self.payable.id)

    def test_hook_respects_existing_counterpart(self):
        """A counterpart set by another module is never overwritten."""
        speeddict = {"account_number": {}}
        st_line_vals = {
            "amount": 250.0,
            "payment_ref": "Import test",
            "counterpart_account_id": self.payable.id,
        }
        self.journal._statement_line_import_update_hook(st_line_vals, speeddict)
        self.assertEqual(st_line_vals["counterpart_account_id"], self.payable.id)

    # ------------------------------------------------------------------
    # Reference-based resolution
    # ------------------------------------------------------------------
    def _make_vendor_bill(self, name, partner):
        """Create and post a vendor bill with an explicit document number."""
        product = self.env["product.product"].create(
            {"name": "Test service", "type": "service", "list_price": 100.0}
        )
        move = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": partner.id,
                "invoice_date": fields.Date.today(),
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "quantity": 1.0,
                            "price_unit": 100.0,
                            "tax_ids": [(5, 0, 0)],
                        },
                    )
                ],
            }
        )
        try:
            move._post()
        except Exception as exc:  # noqa: BLE001 - surface the real reason
            raise AssertionError(f"_post() raised: {type(exc).__name__}: {exc}")
        if move.state != "posted":
            raise AssertionError(
                f"could not post vendor bill: state={move.state} "
                f"journal={move.journal_id.code} name={move.name!r} "
                f"date={move.date} invoice_date={move.invoice_date} "
                f"currency={move.currency_id.name} company_currency={move.company_currency_id.name} "
                f"lines={len(move.invoice_line_ids)}"
            )
        # The document number is assigned by the journal sequence on posting;
        # override it so the test controls the reference it asserts on.
        move.write({"name": name})
        return move

    def _make_customer_invoice(self, name, partner):
        """Create and post a customer invoice with an explicit number."""
        product = self.env["product.product"].create(
            {"name": "Test service", "type": "service", "list_price": 100.0}
        )
        move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": partner.id,
                "invoice_date": fields.Date.today(),
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "quantity": 1.0,
                            "price_unit": 100.0,
                            "tax_ids": [(5, 0, 0)],
                        },
                    )
                ],
            }
        )
        try:
            move._post()
        except Exception as exc:  # noqa: BLE001 - surface the real reason
            raise AssertionError(f"_post() raised: {type(exc).__name__}: {exc}")
        if move.state != "posted":
            raise AssertionError(
                f"could not post vendor bill: state={move.state} "
                f"journal={move.journal_id.code} name={move.name!r} "
                f"date={move.date} invoice_date={move.invoice_date} "
                f"currency={move.currency_id.name} company_currency={move.company_currency_id.name} "
                f"lines={len(move.invoice_line_ids)}"
            )
        # The document number is assigned by the journal sequence on posting;
        # override it so the test controls the reference it asserts on.
        move.write({"name": name})
        return move

    def test_reference_wins_over_positive_amount_for_vendor_bill(self):
        """A vendor bill reference resolves to payable even when the imported
        amount is positive.

        This is the regression that made vendor bills land on 1510: the bank
        encoded the amount as positive (CRDT), so the sign-based fallback picked
        the receivable account. The document reference is the stronger signal.
        """
        partner = self.env["res.partner"].create({"name": "Vendor AB"})
        bill = self._make_vendor_bill("BILL/TEST/0001", partner)
        self.assertEqual(bill.name, "BILL/TEST/0001", "test setup: bill name")
        self.assertEqual(bill.state, "posted", "test setup: posted")
        self.assertEqual(bill.partner_id, partner, "test setup: partner")
        self.assertTrue(
            partner.property_account_payable_id, "test setup: partner payable"
        )
        self.assertEqual(
            self.journal._get_counterpart_from_reference(
                {"amount": 100.0, "payment_ref": bill.name}
            ),
            partner.property_account_payable_id,
            "direct call to _get_counterpart_from_reference",
        )

        speeddict = {"account_number": {}}
        st_line_vals = {
            "amount": 100.0,  # positive, as the bank encoded it
            "payment_ref": bill.name,
        }
        self.journal._statement_line_import_update_hook(st_line_vals, speeddict)
        self.assertEqual(
            st_line_vals.get("counterpart_account_id"),
            partner.property_account_payable_id.id,
        )

    def test_reference_wins_over_negative_amount_for_customer_invoice(self):
        """A customer invoice reference resolves to receivable even when the
        imported amount is negative."""
        partner = self.env["res.partner"].create({"name": "Customer AB"})
        invoice = self._make_customer_invoice("INV/TEST/0001", partner)

        speeddict = {"account_number": {}}
        st_line_vals = {
            "amount": -100.0,
            "payment_ref": invoice.name,
        }
        self.journal._statement_line_import_update_hook(st_line_vals, speeddict)
        self.assertEqual(
            st_line_vals.get("counterpart_account_id"),
            partner.property_account_receivable_id.id,
        )

    def test_reference_with_prefix_text_is_matched(self):
        """Banks often prefix the reference with free text."""
        partner = self.env["res.partner"].create({"name": "Vendor AB"})
        bill = self._make_vendor_bill("BILL/TEST/0002", partner)

        st_line_vals = {
            "amount": 100.0,
            "payment_ref": f"Betalning {bill.name}",
        }
        account = self.journal._get_counterpart_from_reference(st_line_vals)
        self.assertEqual(account, partner.property_account_payable_id)

    def test_unknown_reference_falls_back_to_sign(self):
        """An unmatched reference must not break the sign-based fallback."""
        st_line_vals = {
            "amount": 100.0,
            "payment_ref": "BILL/DOES/NOT/EXIST",
        }
        account = self.journal._get_counterpart_from_reference(st_line_vals)
        self.assertFalse(account)

        speeddict = {"account_number": {}}
        self.journal._statement_line_import_update_hook(st_line_vals, speeddict)
        self.assertEqual(
            st_line_vals.get("counterpart_account_id"), self.receivable.id
        )

    def test_draft_invoice_is_ignored(self):
        """Only posted documents may drive the counterpart."""
        partner = self.env["res.partner"].create({"name": "Vendor AB"})
        product = self.env["product.product"].create(
            {"name": "Test service", "type": "service", "list_price": 100.0}
        )
        draft = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": partner.id,
                "invoice_date": fields.Date.today(),
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "quantity": 1.0,
                            "price_unit": 100.0,
                            "tax_ids": [(5, 0, 0)],
                        },
                    )
                ],
            }
        )
        st_line_vals = {"amount": 100.0, "payment_ref": draft.name or "draft"}
        self.assertFalse(self.journal._get_counterpart_from_reference(st_line_vals))

    def test_reference_tokens(self):
        """The whole reference is tried before its individual tokens."""
        tokens = self.journal._reference_tokens("Betalning BILL/2026/11/0007")
        self.assertEqual(tokens[0], "Betalning BILL/2026/11/0007")
        self.assertIn("BILL/2026/11/0007", tokens)

    # ------------------------------------------------------------------
    # Early-payment discount
    # ------------------------------------------------------------------
    def _make_discount_term(self, percentage=4.0, days=30):
        """Return a payment term offering an early-payment discount."""
        return self.env["account.payment.term"].create(
            {
                "name": f"{percentage}% discount in {days} days",
                "early_discount": True,
                "discount_percentage": percentage,
                "discount_days": days,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "value": "percent",
                            "value_amount": 100.0,
                            "delay_type": "days_after",
                            "nb_days": 45,
                        },
                    )
                ],
            }
        )

    def _make_discounted_bill(self, name, partner, term, price=100.0):
        """Post a vendor bill that carries an early-payment discount."""
        product = self.env["product.product"].create(
            {"name": "Discounted service", "type": "service", "list_price": price}
        )
        tax = self.env["account.tax"].search(
            [
                ("company_id", "=", self.env.company.id),
                ("type_tax_use", "=", "purchase"),
                ("amount", ">", 0),
            ],
            limit=1,
        )
        move = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": partner.id,
                "invoice_date": fields.Date.today(),
                "invoice_payment_term_id": term.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "quantity": 1.0,
                            "price_unit": price,
                            "tax_ids": [(6, 0, tax.ids)],
                        },
                    )
                ],
            }
        )
        move._post()
        self.assertEqual(move.state, "posted", "test setup: bill posted")
        move.write({"name": name})
        return move

    def test_discount_lines_are_added_to_statement_move(self):
        """A discounted payment must book the discount so the entry balances.

        Odoo normally adds those lines during reconciliation. Because this
        module books the counterpart on a real account up front, the module
        has to add them itself - otherwise the entry cannot be reconciled.
        """
        partner = self.env["res.partner"].create({"name": "Discount Vendor"})
        term = self._make_discount_term()
        bill = self._make_discounted_bill("BILL/DISC/0001", partner, term)

        term_line = bill.line_ids.filtered("discount_date")
        self.assertTrue(term_line, "test setup: bill has a discount term line")

        discounted_amount = term_line.discount_balance
        self.assertLess(
            abs(discounted_amount),
            abs(term_line.balance),
            "test setup: discount lowers the amount due",
        )

        st_line = self.env["account.bank.statement.line"].create(
            {
                "journal_id": self.journal.id,
                "payment_ref": bill.name,
                "partner_id": partner.id,
                "amount": discounted_amount,
                "date": fields.Date.today(),
            }
        )

        vals = st_line._prepare_move_line_default_vals()
        move = st_line.move_id

        total_debit = sum(v.get("debit", 0.0) for v in vals)
        total_credit = sum(v.get("credit", 0.0) for v in vals)
        self.assertAlmostEqual(
            total_debit,
            total_credit,
            places=2,
            msg=f"statement move must balance, got D={total_debit} C={total_credit}",
        )

        # The payable must be cleared in full, not just by the paid amount.
        payable_lines = move.line_ids.filtered(
            lambda line: line.account_id.account_type == "liability_payable"
        )
        self.assertAlmostEqual(
            sum(payable_lines.mapped("balance")),
            abs(term_line.balance),
            places=2,
            msg="the full payable must be cleared by payment + discount",
        )

        # The discount must land on the account the company configured for
        # early-payment discounts. Which account that is, and which type it
        # has, is a bookkeeping decision - SFA books it on 3738, an income
        # account - so assert on the configuration, never on the type.
        discount_lines = move.line_ids.filtered(
            lambda line: line.account_id
            == self.env.company.account_journal_early_pay_discount_gain_account_id
        )
        self.assertTrue(
            discount_lines,
            "the discount must land on the company's discount account",
        )
        # With an "included" discount the amount is split between the discount
        # account and the tax lines, exactly as Odoo's own reconciliation
        # does it, so only assert that the account is actually used.
        self.assertNotAlmostEqual(
            sum(discount_lines.mapped("balance")),
            0.0,
            places=2,
            msg="the discount account must carry a balance",
        )
        self.assertFalse(
            move.line_ids.filtered(
                lambda line: self.journal._is_suspense_account(line.account_id)
            ),
            "no line may land on an interim account",
        )

    def test_no_discount_lines_when_window_has_passed(self):
        """After the discount date the full amount is due; no discount lines."""
        partner = self.env["res.partner"].create({"name": "Late Payer"})
        term = self._make_discount_term()
        bill = self._make_discounted_bill("BILL/DISC/0002", partner, term)

        term_line = bill.line_ids.filtered("discount_date")
        late = term_line.discount_date + timedelta(days=1)

        st_line = self.env["account.bank.statement.line"].create(
            {
                "journal_id": self.journal.id,
                "payment_ref": bill.name,
                "partner_id": partner.id,
                "amount": term_line.balance,
                "date": late,
            }
        )
        self.assertEqual(
            st_line._prepare_move_line_default_vals_with_discount(),
            [],
            "no discount lines may be added after the discount date",
        )
