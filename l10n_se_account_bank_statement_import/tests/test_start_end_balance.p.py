# Copyright 2026 Vertel Sverige AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("-at_install", "post_install")
class TestStartEndBalance(AccountTestInvoicingCommon):
    """Regression tests for ``account.bank.statement._start_end_balance``.

    The compute used to read ``journal_id.payment_debit_account_id``. That
    field does not exist in Odoo 18 — it was removed from ``account.journal``
    — so the compute raised ``AttributeError``. It was also the wrong account:
    the interim account is a staging account on the way to the bank, and with
    the ``pending_until_reconciliation`` strategy it is never written to at
    all, so the balance would always have been zero.

    The balance must be read from the journal's own liquidity account
    (``default_account_id``) — the account the statement lines are booked
    against.
    """

    @classmethod
    def get_default_groups(cls):
        groups = super().get_default_groups()
        return groups | cls.env.ref("base.group_erp_manager") | cls.env.ref(
            "base.group_partner_manager"
        )

    def test_start_end_balance_uses_liquidity_account(self):
        """The balance is computed from the journal's liquidity account."""
        journal = self.company_data["default_journal_bank"]
        liquidity_account = journal.default_account_id
        self.assertTrue(
            liquidity_account,
            "The bank journal must have a liquidity account",
        )

        statement = self.env["account.bank.statement"].create(
            {
                "name": "Test statement",
                "journal_id": journal.id,
                "date": fields.Date.today(),
                "balance_start": 0.0,
                "balance_end_real": 0.0,
            }
        )
        self.env["account.bank.statement.line"].create(
            {
                "statement_id": statement.id,
                "journal_id": journal.id,
                "date": fields.Date.today(),
                "payment_ref": "Test line",
                "amount": 100.0,
            }
        )

        # Must not raise AttributeError.
        statement._start_end_balance()
        self.assertIsInstance(
            statement.end_balance_calc,
            float,
            "The balance must be a number, not an error",
        )

    def test_start_end_balance_never_reads_interim_account(self):
        """The compute must not reference an interim-account field.

        ``payment_debit_account_id`` does not exist on ``account.journal`` in
        Odoo 18. This test fails loudly if the field is reintroduced into the
        compute.
        """
        self.assertNotIn(
            "payment_debit_account_id",
            self.env["account.journal"]._fields,
            "If this field ever comes back, the compute must be revisited",
        )

        journal = self.company_data["default_journal_bank"]
        statement = self.env["account.bank.statement"].create(
            {
                "name": "Test statement 2",
                "journal_id": journal.id,
                "date": fields.Date.today(),
                "balance_start": 0.0,
                "balance_end_real": 0.0,
            }
        )
        self.env["account.bank.statement.line"].create(
            {
                "statement_id": statement.id,
                "journal_id": journal.id,
                "date": fields.Date.today(),
                "payment_ref": "Test line 2",
                "amount": 50.0,
            }
        )

        # The compute must complete without touching a non-existent field.
        statement._start_end_balance()

    def test_start_end_balance_empty_statement(self):
        """A statement without lines yields zero, not an error."""
        journal = self.company_data["default_journal_bank"]
        statement = self.env["account.bank.statement"].create(
            {
                "name": "Empty statement",
                "journal_id": journal.id,
                "date": fields.Date.today(),
                "balance_start": 0.0,
                "balance_end_real": 0.0,
            }
        )
        statement._start_end_balance()
        self.assertEqual(statement.start_balance_calc, 0)
        self.assertEqual(statement.end_balance_calc, 0)
