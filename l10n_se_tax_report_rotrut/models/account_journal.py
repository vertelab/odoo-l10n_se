from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    is_rotrut = fields.Boolean(string='Rot/Rut fakturering')
    rotrut_workcost_account_id = fields.Many2one('account.account', string='Rot/Rut arbetskostnader')
    rotrut_material_account_id = fields.Many2one('account.account', string='Rot/Rut matrialkostnader')
    rotrut_receivable_account_id = fields.Many2one('account.account', string='Rot/Rut Kundkodningar')
