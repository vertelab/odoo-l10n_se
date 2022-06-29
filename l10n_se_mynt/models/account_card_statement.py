from odoo import api, fields, models, _, exceptions


import logging
_logger = logging.getLogger(__name__)

class AccountCardStatement(models.Model):
    _name = 'account.card.statement'
    
    date = fields.Date()
    account_card_statement_line_ids = fields.One2many('account.card.statement.line', string='Card Transaction')
    
 
class AccountCardStatementLine(models.Model):
    _name = 'account.card.statement.line'
    date = fields.Date()
    amount = fields.Float()
    currency = fields.Char()
    original_amount = fields.Float()
    original_currency = fields.Float()
    vat_amount = fields.Float()
    vat_rate = fields.Char()
    reverse_vat = fields.Char()
    description	= fields.Char()
    account_Category = fields.Char()
    comment_Filename = fields.Char()
    settlement_status = fields.Char()
    person = fields.Char()
    team = fields.Char()
    card number	= fields.Char()
    card name = fields.Char()
    accounting_status = fields.Char()
