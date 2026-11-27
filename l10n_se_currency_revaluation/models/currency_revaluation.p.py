"""Compute the unrealised currency difference on open monetary items."""
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Only these two account types carry monetary items. Inventory, fixed
# assets and prepayments are non-monetary and must stay at their
# historical rate — K2 ch. and K3 ch. 30 both say so.
MONETARY_ACCOUNT_TYPES = ('asset_receivable', 'liability_payable')


class CurrencyRevaluation(models.Model):
    _name = 'l10n_se.currency.revaluation'
    _description = 'Currency revaluation'
    _order = 'date desc, id desc'

    name = fields.Char(required=True, default='/')
    date = fields.Date(
        required=True, default=fields.Date.context_today,
        help='The revaluation date. Open items are translated at the rate '
             'in force on this date.',
    )
    company_id = fields.Many2one(
        'res.company', required=True,
        default=lambda self: self.env.company,
    )
    line_ids = fields.One2many(
        'l10n_se.currency.revaluation.line', 'revaluation_id',
        string='Lines',
    )
    move_id = fields.Many2one('account.move', string='Revaluation Entry',
                              readonly=True)
    reversal_move_id = fields.Many2one('account.move', string='Reversal',
                                       readonly=True)
    total_amount = fields.Monetary(
        compute='_compute_totals', currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        related='company_id.currency_id', readonly=True,
    )

    @api.depends('line_ids.difference')
    def _compute_totals(self):
        for rec in self:
            rec.total_amount = round(sum(rec.line_ids.mapped('difference')), 2)

    # ------------------------------------------------------------------
    # Computing
    # ------------------------------------------------------------------

    @api.model
    def _ensure_defaults(self, company):
        """Set the default journal and accounts if they are missing.

        l10n_se_extended applies the chart in its own post_init_hook, which
        runs after this module's. The accounts may therefore not exist when
        our hook fires; they are set here on first use instead.
        """
        if (company.currency_revaluation_journal_id
                and company.currency_revaluation_gain_account_id
                and company.currency_revaluation_loss_account_id):
            return
        for code, field in (('3960', 'currency_revaluation_gain_account_id'),
                            ('7960', 'currency_revaluation_loss_account_id')):
            if company[field]:
                continue
            self.env.cr.execute("""
                SELECT aa.id FROM account_account aa
                  JOIN account_account_res_company_rel rel
                    ON rel.account_account_id = aa.id
                 WHERE rel.res_company_id = %s
                   AND EXISTS (
                       SELECT 1 FROM jsonb_each_text(aa.code_store) AS kv(k, v)
                        WHERE kv.v = %s)
                 LIMIT 1
            """, (company.id, code))
            row = self.env.cr.fetchone()
            if row:
                company[field] = row[0]
        if not company.currency_revaluation_journal_id:
            journal = self.env['account.journal'].search([
                ('type', '=', 'general'),
                ('company_id', '=', company.id),
            ], limit=1)
            if journal:
                company.currency_revaluation_journal_id = journal.id

    @api.model
    def _monetary_open_items(self, company, date):
        """Open receivable and payable lines in foreign currency."""
        return self.env['account.move.line'].search([
            ('company_id', '=', company.id),
            ('parent_state', '=', 'posted'),
            ('account_id.account_type', 'in', MONETARY_ACCOUNT_TYPES),
            ('currency_id', '!=', company.currency_id.id),
            ('full_reconcile_id', '=', False),
            ('amount_residual_currency', '!=', 0),
            ('date', '<=', date),
        ])

    @api.model
    def _closing_rate(self, currency, company, date):
        """How many company-currency units one foreign unit is worth.

        res.currency.rate stores the inverse: how many foreign units one
        company unit buys. The rate the revaluation needs is therefore
        1 / rate. Reading it directly gives a difference off by a factor
        of the rate squared.
        """
        stored = self.env['res.currency.rate'].search([
            ('currency_id', '=', currency.id),
            ('company_id', '=', company.id),
            ('name', '<=', date),
        ], order='name desc', limit=1)
        if stored and stored.rate:
            return 1.0 / stored.rate
        if currency.rate:
            return 1.0 / currency.rate
        _logger.warning(
            'currency_revaluation: no rate for %s on %s in company %s',
            currency.name, date, company.name)
        return 1.0

    @api.model
    def _compute_lines(self, company, date):
        """Build the revaluation lines from the open items."""
        groups = {}
        for line in self._monetary_open_items(company, date):
            key = (line.partner_id.id, line.currency_id.id)
            bucket = groups.setdefault(key, {
                'partner_id': line.partner_id.id,
                'currency_id': line.currency_id.id,
                'amount_currency': 0.0,
                'balance': 0.0,
            })
            bucket['amount_currency'] += line.amount_residual_currency
            bucket['balance'] += line.balance

        result = []
        for bucket in groups.values():
            if not bucket['amount_currency']:
                continue
            currency = self.env['res.currency'].browse(bucket['currency_id'])
            closing = self._closing_rate(currency, company, date)
            # Historical rate: what the open balance actually cost in
            # company currency, divided by the foreign amount.
            historical = (bucket['balance'] / bucket['amount_currency']
                          if bucket['amount_currency'] else closing)
            closing_value = company.currency_id.round(
                bucket['amount_currency'] * closing)
            result.append({
                **bucket,
                'historical_rate': historical,
                'closing_rate': closing,
                'closing_value': closing_value,
                'difference': round(closing_value - bucket['balance'], 2),
            })
        return result

    # ------------------------------------------------------------------
    # Creating
    # ------------------------------------------------------------------

    @api.model
    def create_for_date(self, company, date):
        """Build (not post) a revaluation for the date. Idempotent."""
        self._ensure_defaults(company)
        existing = self.search([
            ('company_id', '=', company.id),
            ('date', '=', date),
        ], limit=1)
        if existing:
            raise UserError(_(
                'A revaluation for %(date)s already exists.',
                date=date))
        lines = self._compute_lines(company, date)
        if not lines:
            raise UserError(_(
                'No open monetary items in foreign currency on %s.', date))
        record = self.create({
            'name': _('Revaluation %s', date),
            'date': date,
            'company_id': company.id,
            'line_ids': [(0, 0, line) for line in lines],
        })
        return record


    def action_create_move(self):
        """Post the revaluation and, if configured, its reversal."""
        for rec in self:
            if rec.move_id:
                raise UserError(_(
                    'A revaluation entry already exists for %s.', rec.date))
            company = rec.company_id
            journal = company.currency_revaluation_journal_id
            gain = company.currency_revaluation_gain_account_id
            loss = company.currency_revaluation_loss_account_id
            if not (journal and gain and loss):
                raise UserError(_(
                    'Set the journal and both accounts on the company first.'))

            lines = []
            total = 0.0
            for line in rec.line_ids:
                if not line.difference:
                    continue
                total += line.difference
                # A gain on a receivable is a debit to the receivable and a
                # credit to the gain account; a loss is the reverse.
                if line.difference > 0:
                    lines.append((0, 0, {
                        'name': _('Revaluation %s', line.currency_id.name),
                        'partner_id': line.partner_id.id,
                        'account_id': gain.id,
                        'credit': line.difference,
                        'currency_id': rec.currency_id.id,
                    }))
                else:
                    lines.append((0, 0, {
                        'name': _('Revaluation %s', line.currency_id.name),
                        'partner_id': line.partner_id.id,
                        'account_id': loss.id,
                        'debit': -line.difference,
                        'currency_id': rec.currency_id.id,
                    }))
            if not lines:
                raise UserError(_('Nothing to post: every difference is zero.'))

            # The counter entry: the net on a single balance line, so the
            # move balances without inventing a partner.
            if total > 0:
                lines.append((0, 0, {
                    'name': _('Unrealised currency gain'),
                    'account_id': loss.id,
                    'debit': round(total, 2),
                    'currency_id': rec.currency_id.id,
                }))
            elif total < 0:
                lines.append((0, 0, {
                    'name': _('Unrealised currency loss'),
                    'account_id': gain.id,
                    'credit': round(-total, 2),
                    'currency_id': rec.currency_id.id,
                }))

            move = self.env['account.move'].create({
                'date': rec.date,
                'journal_id': journal.id,
                'company_id': company.id,
                'ref': _('Currency revaluation %s', rec.date),
                'line_ids': lines,
            })
            move.action_post()
            rec.move_id = move.id

            if company.currency_revaluation_reverse:
                reversal_date = self._next_day(rec.date)
                reversal = self.env['account.move'].create({
                    'date': reversal_date,
                    'journal_id': journal.id,
                    'company_id': company.id,
                    'ref': _('Reversal of currency revaluation %s', rec.date),
                    'line_ids': [
                        (0, 0, {
                            'name': line.name,
                            'partner_id': line.partner_id.id,
                            'account_id': line.account_id.id,
                            'debit': line.credit,
                            'credit': line.debit,
                            'currency_id': line.currency_id.id,
                        })
                        for line in move.line_ids
                    ],
                })
                reversal.action_post()
                rec.reversal_move_id = reversal.id
        return True

    @api.model
    def _next_day(self, date):
        from datetime import timedelta
        return date + timedelta(days=1)


class CurrencyRevaluationLine(models.Model):
    _name = 'l10n_se.currency.revaluation.line'
    _description = 'Currency revaluation line'

    revaluation_id = fields.Many2one(
        'l10n_se.currency.revaluation', required=True, ondelete='cascade',
    )
    partner_id = fields.Many2one('res.partner', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  required=True)
    amount_currency = fields.Monetary(
        string='Open Amount', currency_field='currency_id',
    )
    balance = fields.Monetary(
        string='Book Value', currency_field='company_currency_id',
    )
    historical_rate = fields.Float(digits=(12, 6))
    closing_rate = fields.Float(digits=(12, 6))
    closing_value = fields.Monetary(
        string='Closing Value', currency_field='company_currency_id',
    )
    difference = fields.Monetary(
        string='Difference', currency_field='company_currency_id',
    )
    company_currency_id = fields.Many2one(
        related='revaluation_id.currency_id', readonly=True,
    )
