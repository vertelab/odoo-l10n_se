# Copyright 2026 Vertel Sverige AB (<https://vertel.se>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import common, tagged


@tagged('-at_install', 'post_install')
class TestTaxAccountCounterpart(common.TransactionCase):
    """Tax payments must land on 1630, not on the partner's payable account.

    The VAT declaration moves the net VAT from 2650 to 1630. For the bank
    payment to reconcile against that entry, the statement line has to carry
    1630 as its counterpart. The generic counterpart resolution would pick
    2440 (Skatteverket's payable account), which cannot be reconciled
    against 1630.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.AccountAccount = cls.env['account.account']
        cls.company = cls.env.company

        cls.tax_account = cls.AccountAccount.search([
            ('company_ids', 'in', [cls.company.id]),
            ('code', '=', '1630'),
        ], limit=1)
        if not cls.tax_account:
            raise common.SkipTest('Tax account 1630 is not configured')

        cls.skv_partner = cls.env.ref(
            'l10n_se_tax_report.res_partner-SKV', raise_if_not_found=False
        )
        if not cls.skv_partner:
            raise common.SkipTest('Skatteverket partner is not configured')

        cls.journal = cls.env['account.journal'].search([
            ('company_id', '=', cls.company.id),
            ('type', '=', 'bank'),
        ], limit=1)
        if not cls.journal:
            raise common.SkipTest('No bank journal is configured')

    def setUp(self):
        super().setUp()
        # The override is gated on the journal opting out of suspense.
        self.journal.no_suspense_counterpart = True

    def _counterpart(self, vals, speeddict=None):
        return self.journal._get_no_suspense_counterpart(vals, speeddict)

    # ------------------------------------------------------------------
    # Tax account configuration
    # ------------------------------------------------------------------
    def test_configure_makes_tax_account_reconcilable(self):
        """The configuration helper marks 1630 as reconcilable."""
        self.tax_account.reconcile = False
        accounts = self.AccountAccount._l10n_se_tax_report_configure_tax_account()
        self.assertIn(self.tax_account, accounts)
        self.assertTrue(self.tax_account.reconcile)

    def test_configure_is_idempotent(self):
        """Running the configuration twice is harmless."""
        self.AccountAccount._l10n_se_tax_report_configure_tax_account()
        self.AccountAccount._l10n_se_tax_report_configure_tax_account()
        self.assertTrue(self.tax_account.reconcile)

    # ------------------------------------------------------------------
    # Counterpart resolution
    # ------------------------------------------------------------------
    def test_skatteverket_partner_gets_tax_account(self):
        """A line matching the Skatteverket partner books against 1630."""
        counterpart = self._counterpart({
            'partner_id': self.skv_partner.id,
            'amount': -670918.0,
            'payment_ref': 'Betalning skattekonto',
        })
        self.assertEqual(counterpart, self.tax_account)

    def test_tax_keyword_without_partner_gets_tax_account(self):
        """The payment reference alone is enough when no partner matched."""
        counterpart = self._counterpart({
            'partner_id': False,
            'amount': -670918.0,
            'payment_ref': 'Moms mars 2026',
        })
        self.assertEqual(counterpart, self.tax_account)

    def test_unrelated_line_keeps_generic_counterpart(self):
        """A line that is not a tax payment is left alone."""
        other = self.env['res.partner'].create({'name': 'Unrelated Supplier AB'})
        counterpart = self._counterpart({
            'partner_id': other.id,
            'amount': -100.0,
            'payment_ref': 'Faktura 12345',
        })
        self.assertNotEqual(counterpart, self.tax_account)

    def test_journal_without_opt_in_keeps_generic_counterpart(self):
        """Journals still using suspense keep the old behaviour."""
        self.journal.no_suspense_counterpart = False
        counterpart = self._counterpart({
            'partner_id': self.skv_partner.id,
            'amount': -670918.0,
            'payment_ref': 'Betalning skattekonto',
        })
        self.assertNotEqual(counterpart, self.tax_account)

    def test_tax_account_is_a_real_account(self):
        """1630 exists and is reconcilable after configuration."""
        self.AccountAccount._l10n_se_tax_report_configure_tax_account()
        self.assertTrue(self.tax_account.reconcile)
        self.assertNotEqual(self.tax_account.account_type, 'asset_cash')
