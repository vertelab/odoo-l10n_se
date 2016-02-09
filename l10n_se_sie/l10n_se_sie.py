# -*- coding: utf-8 -*-

from openerp import models, fields, api, _
from openerp.exceptions import Warning
import base64

import logging
_logger = logging.getLogger(__name__)

class account_sie(models.TransientModel):
    _name = 'account.sie'
    _description = 'Odoo'
       
    date_start = fields.Date(string = "Start Date")
    date_stop = fields.Date(string = "Stop Date")
    start_period = fields.Many2one(comodel_name = "account.period", string = "Start Period")
    stop_period = fields.Many2one(comodel_name = "account.period", string = "Stop Period")
    fiscal_year = fields.Many2one(comodel_name = "account.fiscalyear", string = "Fiscal Year")
    journal = fields.Many2many(comodel_name = "account.journal", string = "Journal")
    account = fields.Many2many(comodel_name = "account.account", relation='table_name', string = "Account")
    
    state =  fields.Selection([('choose', 'choose'), ('get', 'get')],default="choose") 
    data = fields.Binary('File')
    
    @api.multi
    def send_form(self):
        sie_form = self[0]
        if not sie_form.data == None:
            fileobj = TemporaryFile('w+')
            fileobj.write(base64.decodestring(sie_form.data))
            fileobj.seek(0)
            try:
                pass 
                #~ tools.convert_xml_import(account._cr, 'account_export', fileobj, None, 'init', False, None)
            finally:
                fileobj.close()
            return True
        sie_form.write({'state': 'get', 'data': base64.b64encode(self.make_sie()) })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.sie',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': sie_form.id,
            'views': [(False, 'form')],
            'target': 'new',
        }
    
    @api.multi
    def make_sie(self,search=[]):
        #raise Warning("make_sie: %s %s" %(self,search))
        #  make_sie: account.sie() [('period_id', 'in', [3])] 
        if len(self) > 0:
            sie_form = self[0]
        account_list = set()
        for line in self.env['account.move.line'].search(search):
            account_list.add(line.account_id.code)
        str = ''
        for code in account_list:
            str += '#KONTO %s\n' % code  
        #~ raise Warning("str: %s" % str)  
        
        for ver in self.env['account.move'].search(search):
            str += '#VER "" %s %s "%s" %s %s\n{\n' % (ver.name, ver.date, ver.narration, ver.create_date, ver.create_uid.login)
            
            for trans in ver.line_id:
                str += '#TRANS %s {} %f %s "%s" %s %s \n' % (trans.account_id.code, trans.balance, trans.date, trans.narration, trans.quantity, trans.create_uid.login)
            str += '}\n'    
        
        #TRANS  kontonr {objektlista} belopp  transdat transtext  kvantitet   sign
        #VER    serie vernr verdatum vertext regdatum sign
        
        return str
    
    #~ @api.one
    #~ def make_sie(self,search=[]):
        #~ return self.env['account.move.line'].search(search).account_id.code
        
        
class account_period(models.Model):
    _inherit = 'account.period'
    #~ _name = 'account.period'

    @api.multi
    def make_sie(self,ids):
        return self[0].env['account.sie'].make_sie([('period_id','in',ids)])
        




