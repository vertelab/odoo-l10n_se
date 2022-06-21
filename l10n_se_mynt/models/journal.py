from odoo import api, fields, models, _, exceptions


import logging
_logger = logging.getLogger(__name__)

class AccountJournal(models.Model):
    _inherit = 'account.journal'
    
    is_card_journal = fields.Boolean()
    # ~ card_debit_account = fields.Many2one('account.account', string='Card Debit Account',
    # ~ domain="[('deprecated', '=', False), ('company_id', '=', company_id),"
               # ~ "'|', ('user_type_id', '=', default_account_type),"
               # ~ "('user_type_id.type', '=', 'payable')]")
    # ~ card_credit_account = fields.Many2one('account.account', string='Card Credit Account',
    # ~ domain="[('deprecated', '=', False), ('company_id', '=', company_id),"
               # ~ "'|', ('user_type_id', '=', default_account_type),"
               # ~ "('user_type_id.type', '=', 'receivable')]")
    card_debit_account = fields.Many2one('account.account', string='Card Debit Account')
    card_credit_account = fields.Many2one('account.account', string='Card Credit Account')
    
 
