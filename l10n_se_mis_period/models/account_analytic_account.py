from odoo import models, fields


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    code = fields.Char(
        string='Reference',
        index='btree',
        tracking=True,
        related='name',
        readonly=False
    )