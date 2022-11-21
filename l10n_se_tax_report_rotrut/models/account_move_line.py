from odoo import models, fields, api, _
import logging
_logger = logging.getLogger(__name__)

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    is_rotrut = fields.Boolean(string='Rot/Rut-avdrag', related='move_id.is_rotrut')
    rotrut_id = fields.Many2one('account.rotrut', string='Utfört arbete', store=True)
    rotrut_percent_id = fields.Many2one('account.move', store=True)
    rotrut_percent = fields.Float(related='rotrut_percent_id.rotrut_percent')
