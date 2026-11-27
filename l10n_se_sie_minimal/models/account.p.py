# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import datetime

import logging
_logger = logging.getLogger(__name__)

 
class res_company(models.Model):
    _inherit = 'res.company'
    kptyp = fields.Char(string="Kptyp")
       
class account_account(models.Model):
    _inherit = 'account.account'
    
    def export_sie(self):
        # ~ account_ids = self.env['account.account'].browse(self.ids)
        ver_ids = self.env['account.move'].search([]).filtered(lambda ver: ver.line_ids.filtered(lambda r: r.account_id.code in [a.code for a in self]))
        _logger.warning(f"export_sie {ver_ids}")
        return self.env['account.sie'].export_sie(ver_ids)
        
    def check__missing_accounts(self,accounts):
        missing = []
        for account in accounts:
            if len(self.env['account.account'].search([('code', '=', account[0])])) == 0:
                missing.append(account)
        return missing
        
class account_journal(models.Model):
    _inherit = 'account.journal'

    # FIX FORM ON CLICK
    def send_form(self):
        if len(self > 0):
            sie_form = self[0]
  
    def export_sie(self):
        ver_ids = self.env['account.move'].search([('journal_id', 'in', self.ids)])
        _logger.warning("account journal export sie")
        return self.env['account.sie'].export_sie(ver_ids)


class account_move(models.Model):
    _inherit = 'account.move'
    
    is_incoming_balance_move = fields.Boolean(default = False)

    def export_sie(self):
        # ~ ver_ids = self.env['account.move'].search([('id','in',ids)])
        return self.env['account.sie'].export_sie(self)
        

                    
                    

