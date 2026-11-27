# Copyright 2026 Vertel Sverige AB (<https://vertel.se>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

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
