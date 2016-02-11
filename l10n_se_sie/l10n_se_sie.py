# -*- coding: utf-8 -*-
from cStringIO import StringIO
from openerp import models, fields, api, _
from openerp.exceptions import Warning
from openerp import http
import base64
import tempfile
from werkzeug.datastructures import Headers
from werkzeug.wrappers import Response

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
    
    @api.multi
    def get_accounts(self,ver_ids):
        account_list = set()
        for ver in ver_ids:
            for line in ver.line_id:
            #for l in ver.line_id for ver in ver_ids]]:
                account_list.add(line.account_id)
        return account_list
        
    @api.multi
    def make_sie2(self, ver_ids):
        #raise Warning("make_sie: %s %s" %(self,search))
        #  make_sie: account.sie() [('period_id', 'in', [3])] 
    
        
        if len(self) > 0:
            sie_form = self[0]
        
        str = ''
        for account in self.get_accounts(ver_ids):
            str += '#KONTO %s\n' % account.code
        #raise Warning("str: %s %s search:%s" % (str, self.env['account.move.line'].search(search),search))  
        
        #TRANS  kontonr {objektlista} belopp  transdat transtext  kvantitet   sign
        #VER    serie vernr verdatum vertext regdatum sign
    
        for ver in ver_ids:
            str += '#VER "" %s %s "%s" %s %s\n{\n' % (ver.name, ver.date, self.fix_narration(ver.narration), ver.create_date, ver.create_uid.login)
            #~ str += '#VER "" %s %s "%s" %s %s\n{\n' % (ver.name, ver.date, ver.narration, ver.create_date, ver.create_uid.login)
            
            for trans in ver.line_id:
                str += '#TRANS %s {} %f %s "%s" %s %s \n' % (trans.account_id.code, trans.balance, trans.date, self.fix_narration(trans.name), trans.quantity, trans.create_uid.login)
            str += '}\n'
        _logger.warning('%s' %str)
        return str
    
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
    def export_sie(self,ids):
        ver_ids = self.env['account.move'].search([('period_id','in',ids)])
        _logger.warning('\nver_ids:\n%s' % ver_ids)
        return self.env['account.sie'].make_sie2(ver_ids)
        
    
       
class account_account(models.Model):
    _inherit = 'account.account'
    
    @api.multi
    def export_sie(self,ids):
        account_ids = self.env['account.account'].browse(ids)
        ver_ids = self.env['account.move'].search([]).filtered(lambda ver: ver.line_id.filtered(lambda r: r.account_id.code in [a.code for a in account_ids]))
    
        str = self.env['account.sie'].make_sie2(ver_ids)
        _logger.warning(Response(str,headers=[
                    ('Content-Disposition', 'attachment; filename="l10n_se_sie.sie"'),
                    ('Content-Type', 'text/calendar'),
                    ('Content-Length', len(str)),
                ]))
        return Response(str, headers=[
                    ('Content-Disposition', 'attachment; filename="l10n_se_sie.sie"'),
                    ('Content-Type', 'text/calendar'),
                    ('Content-Length', len(str)),
                ])
        
        
        

class account_fiscalyear(models.Model):
    _inherit = 'account.fiscalyear'
    
    def export_sie(self,ids):
        #fiscal_year_ids = self.env['account.fiscalyear'].browse(ids)
        ver_ids = self.env['account.move'].search([]).filtered(lambda ver: ver.period_id.fiscalyear_id.id in ids)
        #_logger.warning('\n\nfiscal_year\n%s'%ver_ids)

class account_journal(models.Model):
    _inherit = 'account.journal'

    # FIX FORM ON CLICK
    def send_form(self):
        if len(self > 0):
            sie_form = self[0]
        
  
  
    def export_sie(self,ids):
#        _logger.warning('self: %s\nids: %s' %(self,ids))
        ver_ids = self.env['account.move'].search([('journal_id','in',ids)])
 #       _logger.warning('\n%s'%ver_ids)
        self.env['account.sie'].make_sie2(ver_ids)
        self.env['account_kptyp'].get_kptyp(ver_ids)
        
    
## KPTYP GREJEN två klasser. de som ska skapas. lägg på attribut
class account_kptyp(models.Model):
    _inherit = 'account.chart'
    
    @api.multi
    def get_kptyp(self,ids):
        kptyp = self.env['account.chart'].browse(ids)
        _logger.warning('\nKPTYP STUFF PARENT\n%s'%kptyp)
    
class account_kptyp_child(account_kptyp):
    
    @api.multi
    def get_kptyp(self,ids):
        _logger.warning('\nGET_KPTYP CHILD\n%s'%ids)
        super(account_kptyp_child,self).get_kptyp(ids)
