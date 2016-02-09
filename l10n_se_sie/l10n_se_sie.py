# -*- coding: utf-8 -*-
from cStringIO import StringIO
from openerp import models, fields, api, _
from openerp.exceptions import Warning
from openerp import http
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
            # select * from account_period where accunt_period.period_id >= p1 and accunt_period.period_id <= p2
            
        ## TODO: plenty of if cases to know what's selected. id is integer
        if(sie_form.start_period.id and sie_form.stop_period.id):
            period_ids = [p.id for p in sie_form.env['account.period'].search(['&',('id','>=',sie_form.start_period.id),('id','>=',sie_form.stop_period.id)])]
            s = [('period_id','in',period_ids)]
        else:
            s = [('period_id','in',[])]
        #raise Warning(s)
        sie_form.write({'state': 'get', 'data': base64.b64encode(self.make_sie(search=s)) })
        #~ sie_form.write({'state': 'get', 'data': base64.b64encode(self.make_sie()) })
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
        #raise Warning("str: %s %s search:%s" % (str, self.env['account.move.line'].search(search),search))  
        
        #TRANS  kontonr {objektlista} belopp  transdat transtext  kvantitet   sign
        #VER    serie vernr verdatum vertext regdatum sign
    
        for ver in self.env['account.move'].search(search):
            str += '#VER "" %s %s "%s" %s %s\n{\n' % (ver.name, ver.date, self.fix_narration(ver.narration), ver.create_date, ver.create_uid.login)
            #~ str += '#VER "" %s %s "%s" %s %s\n{\n' % (ver.name, ver.date, ver.narration, ver.create_date, ver.create_uid.login)
            
            for trans in ver.line_id:
                str += '#TRANS %s {} %f %s "%s" %s %s \n' % (trans.account_id.code, trans.balance, trans.date, self.fix_narration(trans.name), trans.quantity, trans.create_uid.login)
            str += '}\n'
        return str
    
    #~ @api.one
    #~ def make_sie(self,search=[]):
        #~ return self.env['account.move.line'].search(search).account_id.code
        
    # if narration is null, return empty string instead of parsing to False
    @api.multi
    def fix_narration(self, narration):
        if(narration):
            return narration
        else:
            return ''
        
class account_period(models.Model):
    _inherit = 'account.period'
    
    @api.multi
    def do_it(self,ids):
        periods = self.get_period(ids)
        #raise Warning(periods)
        _logger.warning('do_it sie %s' %base64.encodestring(periods.encode('utf-8')))
        http.send_file(StringIO(periods.encode('utf-8')),filename='period.sie')
        #>>> base64.b64encode(u'\xfc\xf1\xf4'.encode('utf-8'))
        #~ return http.send_file(StringIO(self.run(self.data_to_img(getattr(o, field))).make_blob(format='jpg')), filename=field, mtime=self.get_mtime(o))
        
        #self.write_to_file(periods)
    
    def get_period(self,ids):
        return self.env['account.sie'].make_sie([('period_id','in',ids)])
        
      
        

class account_account(models.Model):
    _inherit = 'account.account'
    
    @api.multi
    def get_account(self,ids):
        if(len(self) > 0):
            return self[0].env['account.sie'].make_sie([('id','in',ids)])
        else:
            return self.env['account.sie'].make_sie([('id','in',ids)])
