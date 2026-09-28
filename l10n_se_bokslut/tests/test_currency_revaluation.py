# Copyright 2026 Vertel AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields
from odoo.tests import tagged, TransactionCase


@tagged("post_install", "-at_install")
class TestCurrencyRevaluation(TransactionCase):
    """Currency revaluation of open AR/AP items at year-end.

    Mirrors the known NOK case (cf. T/11500, T/11501): an open invoice in a
    foreign currency must be revalued at the closing rate so the balance
    sheet shows the correct SEK amount.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.company = cls.env.ref("base.main_company")
        cls.company_currency = cls.company.currency_id

        cls.currency_nok = cls.env["res.currency"].search(
            [("name", "=", "NOK")], limit=1)
        if not cls.currency_nok:
            cls.currency_nok = cls.env["res.currency"].create({
                "name": "NOK",
                "symbol": "kr",
                "rate": 1.0,
            })
        cls.currency_nok.active = True

        cls.partner = cls.env["res.partner"].create({
            "name": "Test NOK Customer",
        })

        # A general journal for the revaluation entry
        cls.journal = cls.env["account.journal"].search([
            ("type", "=", "general"),
            ("company_id", "=", cls.company.id),
        ], limit=1)
        if not cls.journal:
            cls.journal = cls.env["account.journal"].create({
                "name": "Misc",
                "code": "MISC",
                "type": "general",
                "company_id": cls.company.id,
            })

    def _make_bokslut(self, closing_date):
        """Create a minimal account.bokslut for the given closing date."""
        period = self.env["account.period"].search([
            ("company_id", "=", self.company.id),
            ("date_stop", ">=", closing_date),
        ], order="date_stop asc", limit=1)
        if not period:
            period = self.env["account.period"].search([
                ("company_id", "=", self.company.id),
            ], order="date_stop desc", limit=1)
        return self.env["account.bokslut"].create({
            "name": "Test Bokslut",
            "company_id": self.company.id,
            "period_stop": period.id,
        })

    def test_revaluation_difference_compute(self):
        """difference = amount_foreign * closing_rate - booked (SEK)."""
        bokslut = self._make_bokslut(fields.Date.today())
        rec = self.env["account.bokslut.currency.revaluation"].create({
            "bokslut_id": bokslut.id,
            "partner_id": self.partner.id,
            "currency_id": self.currency_nok.id,
            "amount_foreign": 10000.0,
            "rate_booking": 1.00,
            "rate_closing": 1.05,
            "amount_company_booking": 10000.0,
        })
        self.assertAlmostEqual(rec.amount_company_closing, 10500.0, places=2)
        self.assertAlmostEqual(rec.difference, 500.0, places=2)

    def test_revaluation_payable_sign(self):
        """A payable revaluation line keeps the sign of the difference."""
        bokslut = self._make_bokslut(fields.Date.today())
        rec = self.env["account.bokslut.currency.revaluation"].create({
            "bokslut_id": bokslut.id,
            "partner_id": self.partner.id,
            "currency_id": self.currency_nok.id,
            "amount_foreign": -10000.0,
            "rate_booking": 1.00,
            "rate_closing": 1.05,
            "amount_company_booking": -10000.0,
        })
        self.assertAlmostEqual(rec.amount_company_closing, -10500.0, places=2)
        self.assertAlmostEqual(rec.difference, -500.0, places=2)

    def test_total_currency_difference_on_bokslut(self):
        """The closing aggregates all revaluation lines."""
        bokslut = self._make_bokslut(fields.Date.today())
        self.env["account.bokslut.currency.revaluation"].create([
            {
                "bokslut_id": bokslut.id,
                "currency_id": self.currency_nok.id,
                "amount_foreign": 10000.0,
                "rate_booking": 1.00,
                "rate_closing": 1.05,
                "amount_company_booking": 10000.0,
            },
            {
                "bokslut_id": bokslut.id,
                "currency_id": self.currency_nok.id,
                "amount_foreign": 2000.0,
                "rate_booking": 1.00,
                "rate_closing": 0.95,
                "amount_company_booking": 2000.0,
            },
        ])
        bokslut._compute_total_currency_difference()
        self.assertAlmostEqual(bokslut.total_currency_difference, 400.0, places=2)
