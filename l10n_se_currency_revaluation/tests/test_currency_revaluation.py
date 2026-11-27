# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Revaluation of open monetary items in foreign currency."""
import datetime

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'l10n_se_currency_revaluation')
class TestCurrencyRevaluation(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.eur = cls.env.ref('base.EUR')
        cls.eur.active = True
        cls.partner = cls.env['res.partner'].create({'name': 'Test AB'})

        cls.income = cls.env['account.account'].search([
            ('account_type', '=', 'income'),
            ('company_ids', 'in', cls.company.id),
        ], limit=1)
        if not cls.income:
            cls.skipTest('no income account in the chart')

        # The test database runs generic_coa, which has no 3960/7960.
        # Create the pair so the configuration step can find them.
        cls.gain = cls.env['account.account'].create({
            'name': 'Currency gain', 'code': '3960',
            'account_type': 'income', 'company_ids': [(6, 0, [cls.company.id])],
        })
        cls.loss = cls.env['account.account'].create({
            'name': 'Currency loss', 'code': '7960',
            'account_type': 'expense_direct_cost',
            'company_ids': [(6, 0, [cls.company.id])],
        })
        cls.journal = cls.env['account.journal'].search([
            ('type', '=', 'general'),
            ('company_id', '=', cls.company.id),
        ], limit=1)
        if not cls.journal:
            cls.skipTest('no general journal')

        # 1 EUR = 11 SEK at the invoice, 12 SEK at the closing date.
        # res.currency.rate stores the inverse.
        for name, rate in (('2024-01-01', 1 / 11.0),
                           ('2024-12-31', 1 / 12.0)):
            cls.env['res.currency.rate'].create({
                'currency_id': cls.eur.id,
                'company_id': cls.company.id,
                'name': name,
                'rate': rate,
            })

    def _invoice(self, amount=1000.0, currency=None):
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'company_id': self.company.id,
            'currency_id': (currency or self.eur).id,
            'invoice_date': '2024-06-01',
            'date': '2024-06-01',
            'invoice_line_ids': [(0, 0, {
                'name': 'Test',
                'quantity': 1,
                'price_unit': amount,
                'account_id': self.income.id,
            })],
        })
        move.action_post()
        return move

    def test_difference_is_computed(self):
        """1000 EUR at 11, closed at 12, gives 1000 SEK."""
        self._invoice()
        R = self.env['l10n_se.currency.revaluation']
        lines = R._compute_lines(self.company, datetime.date(2024, 12, 31))
        mine = [l for l in lines if l['partner_id'] == self.partner.id]
        self.assertTrue(mine, 'the invoice is not in the open items')
        self.assertAlmostEqual(mine[0]['difference'], 1000.0, places=2)

    def test_non_monetary_is_excluded(self):
        """An entry on a non-monetary account is not revalued."""
        expense = self.env['account.account'].search([
            ('account_type', 'in', ['expense', 'expense_direct_cost']),
            ('company_ids', 'in', self.company.id),
        ], limit=1)
        if not expense:
            self.skipTest('no expense account')
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'company_id': self.company.id,
            'currency_id': self.eur.id,
            'date': '2024-06-01',
            'line_ids': [
                (0, 0, {'name': 'Prepaid', 'account_id': expense.id,
                        'debit': 11000.0, 'currency_id': self.eur.id,
                        'amount_currency': 1000.0}),
                (0, 0, {'name': 'Counter', 'account_id': self.income.id,
                        'credit': 11000.0, 'currency_id': self.eur.id,
                        'amount_currency': -1000.0}),
            ],
        })
        move.action_post()
        R = self.env['l10n_se.currency.revaluation']
        lines = R._compute_lines(self.company, datetime.date(2024, 12, 31))
        self.assertFalse(
            [l for l in lines if l['partner_id'] == self.partner.id
             and l['difference']],
            'a non-monetary item was revalued')

    def test_posting_creates_reversal(self):
        """The entry balances and the reversal turns it around."""
        self._invoice()
        R = self.env['l10n_se.currency.revaluation']
        R._ensure_defaults(self.company)
        rec = R.create_for_date(self.company, datetime.date(2024, 12, 31))
        rec.action_create_move()
        self.assertTrue(rec.move_id)
        self.assertTrue(rec.reversal_move_id)
        self.assertEqual(rec.reversal_move_id.date,
                         datetime.date(2025, 1, 1))
        for move in (rec.move_id, rec.reversal_move_id):
            debit = sum(move.line_ids.mapped('debit'))
            credit = sum(move.line_ids.mapped('credit'))
            self.assertAlmostEqual(debit, credit, places=2)

    def test_second_run_for_same_date_is_refused(self):
        """A revaluation for a date can only exist once."""
        self._invoice()
        R = self.env['l10n_se.currency.revaluation']
        R._ensure_defaults(self.company)
        R.create_for_date(self.company, datetime.date(2024, 12, 31))
        with self.assertRaises(UserError):
            R.create_for_date(self.company, datetime.date(2024, 12, 31))
