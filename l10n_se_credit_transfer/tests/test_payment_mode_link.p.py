# Copyright 2026 Vertel Sverige AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.exceptions import ValidationError
from odoo.tests import tagged, TransactionCase

from ..hooks import _ensure_payment_modes
from ..models.account_payment_method import SE_PAYMENT_METHOD_CODES


@tagged("post_install", "-at_install")
class TestSePaymentModeLink(TransactionCase):
    """Every Swedish (ISO 20022) payment method must be reachable from a mode."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.company = cls.env.ref("base.main_company")
        cls.bank_journal = cls.env["account.journal"].create(
            {
                "name": "SE Link Bank Journal",
                "type": "bank",
                "code": "SELK",
                "company_id": cls.company.id,
            }
        )
        cls.methods = cls.env["account.payment.method"].search(
            [
                ("code", "in", list(SE_PAYMENT_METHOD_CODES)),
                ("payment_type", "=", "outbound"),
            ]
        )

    def _modes(self, method):
        return self.env["account.payment.mode"].with_context(
            active_test=False
        ).search(
            [
                ("payment_method_id", "=", method.id),
                ("company_id", "=", self.company.id),
            ]
        )

    def test_01_methods_exist(self):
        codes = set(self.methods.mapped("code"))
        self.assertEqual(codes, set(SE_PAYMENT_METHOD_CODES))

    def test_02_hook_creates_one_mode_per_method(self):
        """The post-init hook gives every SE method a usable payment mode."""
        # Simulate an install where the methods exist but no mode was created
        # yet. The methods are archived for the duration of the test so the
        # orphan guard does not fire on the unlink (the guard only looks at
        # active modes, which is what the user actually sees).
        self.methods.write({"active": False})
        for method in self.methods:
            # Modes already used on journal items cannot be deleted; archive
            # them instead, which is what a user would do in the UI.
            modes = self._modes(method)
            if modes:
                modes.write({"active": False})
        self.methods.write({"active": True})

        _ensure_payment_modes(self.env)

        for method in self.methods:
            mode = self._modes(method).filtered("active")
            self.assertEqual(
                len(mode), 1, "Expected exactly one mode for %s" % method.code
            )
            self.assertEqual(mode.payment_type, "outbound")
            self.assertEqual(mode.bank_account_link, "fixed")
            self.assertTrue(mode.fixed_journal_id)

    def test_03_hook_is_idempotent(self):
        """Re-running the hook must not duplicate the payment modes."""
        _ensure_payment_modes(self.env)
        first = {m.code: self._modes(m).ids for m in self.methods}

        _ensure_payment_modes(self.env)

        for method in self.methods:
            self.assertEqual(self._modes(method).ids, first[method.code])

    def test_04_order_can_be_created_from_mode(self):
        """A mode created by the hook is enough to build a payment order."""
        self.bank_journal.unlink()
        _ensure_payment_modes(self.env)
        method = self.methods.filtered(lambda m: m.code == "se_credit_transfer")
        mode = self._modes(method)

        order = self.env["account.payment.order"].create(
            {
                "payment_type": "outbound",
                "payment_mode_id": mode.id,
                "company_id": self.company.id,
            }
        )
        self.assertEqual(order.payment_method_id, method)
        self.assertEqual(order.journal_id, mode.fixed_journal_id)

    def test_05_mode_cannot_leave_method_orphaned(self):
        """Unlinking the last mode of a SE method is refused."""
        _ensure_payment_modes(self.env)
        method = self.methods.filtered(lambda m: m.code == "se_credit_transfer_20")
        mode = self._modes(method)
        self.assertEqual(len(mode), 1)

        with self.assertRaises(ValidationError):
            mode.unlink()

    def test_06_archiving_the_method_releases_the_guard(self):
        """An archived method may lose its mode — it is no longer offered."""
        _ensure_payment_modes(self.env)
        method = self.methods.filtered(lambda m: m.code == "se_credit_transfer_20")
        mode = self._modes(method)

        method.write({"active": False})
        mode.unlink()
        self.assertFalse(self._modes(method))
