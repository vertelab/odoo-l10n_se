"""IAS 21 translation of the closing for group consolidation.

The Swedish accounts are kept in SEK. When the parent consolidates, the
figures are translated to the group currency:

    assets and liabilities   closing rate
    income and expenses      average rate over the year
    equity                   historical rate
    the difference           a translation reserve in equity, not profit

Nothing here is booked. The translation difference belongs to the group
accounts, not to the Swedish company.
"""
import base64
import csv
import io
import json
import logging
from datetime import date

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Asset and liability accounts are translated at the closing rate; income
# and expense accounts at the average. Equity accounts are historical.
CLOSING_TYPES = (
    'asset_receivable', 'asset_cash', 'asset_current', 'asset_non_current',
    'asset_prepayments', 'asset_fixed',
    'liability_payable', 'liability_current', 'liability_non_current',
)
AVERAGE_TYPES = ('income', 'income_other', 'expense', 'expense_depreciation',
                 'expense_direct_cost')
EQUITY_TYPES = ('equity', 'equity_unaffected')


class BokslutConsolidation(models.Model):
    _inherit = 'account.bokslut'

    consolidation_currency_id = fields.Many2one(
        'res.currency', string='Group Currency',
        help='The currency the parent consolidates in. Defaults to the '
             'company currency, in which case nothing is translated.',
    )

    # ------------------------------------------------------------------
    # Rates
    # ------------------------------------------------------------------

    def _rate_on(self, currency, company, on_date):
        """How many company-currency units one foreign unit is worth.

        res.currency.rate stores the inverse, as in
        l10n_se_currency_revaluation.
        """
        stored = self.env['res.currency.rate'].search([
            ('currency_id', '=', currency.id),
            ('company_id', '=', company.id),
            ('name', '<=', on_date),
        ], order='name desc', limit=1)
        if stored and stored.rate:
            return 1.0 / stored.rate
        if currency.rate:
            return 1.0 / currency.rate
        _logger.warning(
            'consolidation: no rate for %s on %s in company %s',
            currency.name, on_date, company.name)
        return 1.0

    def _average_rate(self, currency, company, date_from, date_to):
        """Mean of the daily rates over the period.

        IAS 21 allows an average rate when rates do not fluctuate
        significantly; it is closer to the transaction rates than the
        closing rate would be.
        """
        rates = self.env['res.currency.rate'].search([
            ('currency_id', '=', currency.id),
            ('company_id', '=', company.id),
            ('name', '>=', date_from),
            ('name', '<=', date_to),
        ], order='name')
        if not rates:
            return self._rate_on(currency, company, date_to)
        values = [1.0 / r.rate for r in rates if r.rate]
        return sum(values) / len(values) if values else 1.0

    # ------------------------------------------------------------------
    # The figures
    # ------------------------------------------------------------------

    def _balance_by_account(self):
        """Saldobalans for the period, per account."""
        self.ensure_one()
        if not self.period_stop:
            raise UserError(_('Set the end period first.'))
        start = self.date_start
        stop = self.period_stop.date_stop
        self.env.cr.execute("""
            SELECT aa.id, aa.code_store, aa.name, aa.account_type,
                   sum(aml.balance)::numeric(14,2)
              FROM account_move_line aml
              JOIN account_move am ON am.id = aml.move_id
              JOIN account_account aa ON aa.id = aml.account_id
             WHERE am.company_id = %s
               AND am.state = 'posted'
               AND aml.date >= %s AND aml.date <= %s
             GROUP BY aa.id, aa.code_store, aa.name, aa.account_type
             HAVING sum(aml.balance) <> 0
             ORDER BY aa.id
        """, (self.company_id.id, start, stop))
        return self.env.cr.fetchall()

    def _consolidation_data(self):
        """Translate the figures to the group currency."""
        self.ensure_one()
        company = self.company_id
        target = self.consolidation_currency_id or company.currency_id
        stop = self.period_stop.date_stop
        start = self.date_start

        if target == company.currency_id:
            closing = average = 1.0
        else:
            closing = self._rate_on(target, company, stop)
            average = self._average_rate(target, company, start, stop)

        rows = []
        translated = {'assets': 0.0, 'liabilities': 0.0, 'equity': 0.0,
                      'result': 0.0}
        for acc_id, code_store, name, acc_type, balance in \
                self._balance_by_account():
            balance = float(balance)
            code = (code_store or {}).get('1') or (code_store or {}).get('3') or ''
            if acc_type in AVERAGE_TYPES:
                rate, bucket = average, 'result'
            elif acc_type in EQUITY_TYPES:
                rate, bucket = closing, 'equity'
            elif acc_type.startswith('asset_'):
                rate, bucket = closing, 'assets'
            elif acc_type.startswith('liability_'):
                rate, bucket = closing, 'liabilities'
            else:
                rate, bucket = closing, 'equity'
            amount = round(balance * rate, 2)
            translated[bucket] += amount
            rows.append({
                'code': code,
                'name': name if isinstance(name, str) else name.get('en_US', ''),
                'account_type': acc_type,
                'balance': round(balance, 2),
                'rate': round(rate, 6),
                'translated': amount,
            })

        # The raw balances sum to zero: every debit has a credit. The
        # translation difference is therefore simply the sum of the
        # translated amounts — when the rates are all 1,0 it is zero.
        difference = round(sum(r['translated'] for r in rows), 2)

        return {
            'company': company.name,
            'fiscal_year': self.fiscalyear_id.name,
            'date_from': str(start),
            'date_to': str(stop),
            'company_currency': company.currency_id.name,
            'group_currency': target.name,
            'closing_rate': round(closing, 6),
            'average_rate': round(average, 6),
            'accounts': rows,
            'translation_difference': difference,
            'note': (
                'Equity is translated at the closing rate. A stricter IAS 21 '
                'reading uses the historical rate for each equity '
                'transaction; this export does not reconstruct that history.'
            ),
        }

    # ------------------------------------------------------------------
    # Exports
    # ------------------------------------------------------------------

    def action_export_consolidation_json(self):
        """Download the consolidation figures as JSON."""
        self.ensure_one()
        data = self._consolidation_data()
        payload = json.dumps(data, ensure_ascii=False, indent=1)
        attachment = self.env['ir.attachment'].create({
            'name': f'consolidation-{data["date_to"]}.json',
            'datas': base64.b64encode(payload.encode('utf-8')),
            'mimetype': 'application/json',
            'res_model': self._name,
            'res_id': self.id,
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def action_export_consolidation_csv(self):
        """Download the consolidation figures as CSV."""
        self.ensure_one()
        data = self._consolidation_data()
        output = io.StringIO()
        writer = csv.writer(output, delimiter=';')
        writer.writerow(['Company', data['company']])
        writer.writerow(['Fiscal year', data['fiscal_year']])
        writer.writerow(['Period', f'{data["date_from"]} .. {data["date_to"]}'])
        writer.writerow(['Group currency', data['group_currency']])
        writer.writerow(['Closing rate', data['closing_rate']])
        writer.writerow(['Average rate', data['average_rate']])
        writer.writerow([])
        writer.writerow(['Code', 'Name', 'Type', 'Balance',
                         'Rate', 'Translated'])
        for row in data['accounts']:
            writer.writerow([row['code'], row['name'], row['account_type'],
                             row['balance'], row['rate'], row['translated']])
        writer.writerow([])
        writer.writerow(['Translation difference',
                         data['translation_difference']])
        payload = output.getvalue()
        attachment = self.env['ir.attachment'].create({
            'name': f'consolidation-{data["date_to"]}.csv',
            'datas': base64.b64encode(payload.encode('utf-8')),
            'mimetype': 'text/csv',
            'res_model': self._name,
            'res_id': self.id,
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
