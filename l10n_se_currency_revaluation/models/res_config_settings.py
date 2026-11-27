from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    currency_revaluation_journal_id = fields.Many2one(
        related='company_id.currency_revaluation_journal_id', readonly=False)
    currency_revaluation_gain_account_id = fields.Many2one(
        related='company_id.currency_revaluation_gain_account_id',
        readonly=False)
    currency_revaluation_loss_account_id = fields.Many2one(
        related='company_id.currency_revaluation_loss_account_id',
        readonly=False)
    currency_revaluation_reverse = fields.Boolean(
        related='company_id.currency_revaluation_reverse', readonly=False)
