from odoo import models, fields, api, _


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # is_rotrut_id = fields.Many2one('account.move', string='is_rotrut')
    is_rotrut = fields.Boolean(string='RotRut avdrag', related='move_id.is_rotrut')
    rotrut_id = fields.Many2one('account.rotrut', string='Rotrut', store=True)
    # name_id = fields.Many2one('account.rotrut', string='Utfört arbete')
