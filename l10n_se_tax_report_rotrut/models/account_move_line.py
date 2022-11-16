from odoo import models, fields, api, _


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    is_rotrut = fields.Boolean(string='Rot/Rut-avdrag', related='move_id.is_rotrut')
    rotrut_id = fields.Many2one('account.rotrut', string='Utfört arbete', store=True)
