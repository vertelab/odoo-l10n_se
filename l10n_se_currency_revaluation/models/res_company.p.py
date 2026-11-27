"""Configuration for the currency revaluation."""
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    currency_revaluation_journal_id = fields.Many2one(
        'account.journal', string='Revaluation Journal',
        domain="[('type', '=', 'general'), ('company_id', '=', id)]",
        help='Journal for the revaluation entry and its reversal.',
    )
    currency_revaluation_gain_account_id = fields.Many2one(
        'account.account', string='Gain Account',
        domain="[('account_type', '=', 'income'), ('company_ids', 'in', id)]",
        help='Where unrealised gains post. BAS 3960 for operating '
             'receivables and payables.',
    )
    currency_revaluation_loss_account_id = fields.Many2one(
        'account.account', string='Loss Account',
        domain="[('account_type', 'in', ['expense', 'expense_direct_cost']), "
               "('company_ids', 'in', id)]",
        help='Where unrealised losses post. BAS 7960 for operating '
             'receivables and payables.',
    )
    currency_revaluation_reverse = fields.Boolean(
        string='Create Reversal', default=True,
        help='Create the reversal entry at the same time, dated the first '
             'day of the next period. Without it the revaluation would be '
             'counted twice when the invoice is eventually settled.',
    )
