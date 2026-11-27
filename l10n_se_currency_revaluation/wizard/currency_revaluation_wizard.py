"""Wizard: preview the revaluation, then post it with its reversal."""
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class CurrencyRevaluationWizard(models.TransientModel):
    _name = 'l10n_se.currency.revaluation.wizard'
    _description = 'Currency revaluation'

    date = fields.Date(
        required=True, default=fields.Date.context_today,
        help='Translate open monetary items at the rate in force on this date.',
    )
    company_id = fields.Many2one(
        'res.company', required=True,
        default=lambda self: self.env.company,
    )
    preview = fields.Text(
        compute='_compute_preview', readonly=True,
        help='What the revaluation would post. Nothing is booked yet.',
    )
    line_count = fields.Integer(compute='_compute_preview')
    total = fields.Monetary(compute='_compute_preview',
                            currency_field='currency_id')
    currency_id = fields.Many2one(related='company_id.currency_id')

    @api.depends('date', 'company_id')
    def _compute_preview(self):
        R = self.env['l10n_se.currency.revaluation']
        for wiz in self:
            if not (wiz.date and wiz.company_id):
                wiz.preview = False
                wiz.line_count = 0
                wiz.total = 0.0
                continue
            lines = R._compute_lines(wiz.company_id, wiz.date)
            wiz.line_count = len(lines)
            wiz.total = round(sum(l['difference'] for l in lines), 2)
            if not lines:
                wiz.preview = _('No open monetary items in foreign currency.')
                continue
            rows = []
            for l in lines:
                partner = self.env['res.partner'].browse(l['partner_id'])
                currency = self.env['res.currency'].browse(l['currency_id'])
                rows.append(
                    f'{partner.name[:28]:<30} {currency.name} '
                    f'{l["amount_currency"]:>12.2f} '
                    f'{l["historical_rate"]:>10.4f} {l["closing_rate"]:>10.4f} '
                    f'{l["difference"]:>12.2f}')
            header = (f'{"Partner":<30} {"Cur":<4} {"Open":>12} '
                      f'{"Hist":>10} {"Close":>10} {"Diff":>12}')
            wiz.preview = '\n'.join([header] + rows)

    def action_post(self):
        """Create the revaluation and, if configured, its reversal."""
        self.ensure_one()
        R = self.env['l10n_se.currency.revaluation']
        company = self.company_id
        if not company.currency_revaluation_journal_id:
            raise UserError(_(
                'Set a revaluation journal on the company first.'))
        if not (company.currency_revaluation_gain_account_id
                and company.currency_revaluation_loss_account_id):
            raise UserError(_(
                'Set both the gain and the loss account first.'))
        record = R.create_for_date(company, self.date)
        record.action_create_move()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'l10n_se.currency.revaluation',
            'res_id': record.id,
            'view_mode': 'form',
            'target': 'current',
        }
