from odoo import api, fields, models, _, exceptions


import logging
_logger = logging.getLogger(__name__)

class AccountCardStatement(models.Model):
    _name = 'account.card.statement'
    _inherit = ['mail.thread']
    name = fields.Char()
    date = fields.Date()
    account_card_statement_line_ids = fields.One2many('account.card.statement.line', 'account_card_statement_id', string='Card Transaction')
    account_move_id = fields.Many2one('account.move', string='Entry')
    journal_id = fields.Many2one('account.journal', string='journal')
    
    
    def unlink(self):
        for record in self:
            record.account_card_statement_line_ids.unlink()
        return super(AccountCardStatement, self).unlink()

    
    
    
 
class AccountCardStatementLine(models.Model):
    _name = 'account.card.statement.line'
    account_card_statement_id = fields.Many2one('account.card.statement', string='Card Transaction', required=True)
    account_move_id = fields.Many2one('account.move', string='Entry', required=True)
    date = fields.Date()
    amount = fields.Float()
    currency = fields.Many2one('res.currency', string='Currency')###res.currency
    original_amount = fields.Float()
    original_currency = fields.Char()
    vat_amount = fields.Float()
    vat_rate = fields.Char()
    reverse_vat = fields.Char()
    description	= fields.Char()
    account = fields.Many2one('account.account', string='Account')
    category = fields.Char()
    comment = fields.Char()
    filename = fields.Char()
    settlement_status = fields.Char()
    person = fields.Char()
    team = fields.Char()
    card_number	= fields.Char()
    card_name = fields.Char()
    accounting_status = fields.Char()

