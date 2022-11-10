from odoo import models, fields, api, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    is_rotrut = fields.Boolean(string='RotRut avdrag')
    # rotrut_id = fields.Many2one('account.rotrut', string='rotrut')
