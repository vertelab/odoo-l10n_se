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
    def get_fiscalyears(self,ver_ids):
        year_list = set()
        for ver in ver_ids:
            year_list.add(ver.period_id.fiscalyear_id)
        return year_list
        
    
    @api.multi
    def make_sie2(self, ver_ids):
        if len(self) > 0:
            sie_form = self[0]
        
        company = ver_ids[0].company_id
        fiscalyear = ver_ids[0].period_id.fiscalyear_id
        user = self.env['res.users'].browse(self._context['uid'])

        str = ''
        str += '#FLAGGA 0\n' 
        str += '#PROGRAM "Odoo" 8.0.1\n'
        str += '#FORMAT PC8, Anger vilken teckenuppsattning som anvants\n'
        str += '#GEN %s\n'%fields.Date.today().replace('-','')
        str += '#SIETYP 4i\n'
        for fiscalyear in self.get_fiscalyears(ver_ids):
            str += '#RAR %s %s %s\n' %(fiscalyear.get_rar_code(), fiscalyear.date_start.replace('-',''), fiscalyear.date_stop.replace('-',''))
        str += '#ORGNR %s\n' %company.company_registry
        str += '#ADRESS "%s" "%s" "%s %s" "%s"\n' %(user.display_name, company.street, company.zip, company.city, company.phone)
        str += '#KPTYP %s\n' % company.kptyp
        for account in self.get_accounts(ver_ids):
            str += '#KONTO %s "%s"\n' % (account.code, account.name)
            
        #raise Warning("str: %s %s search:%s" % (str, self.env['account.move.line'].search(search),search))  
        
        #TRANS  kontonr {objektlista} belopp  transdat transtext  kvantitet   sign
        #VER    serie vernr verdatum vertext regdatum sign
    
        for ver in ver_ids:
            str += '#VER "" %s %s "%s" %s %s\n{\n' % (ver.name, ver.date.replace('-',''), self.fix_empty(ver.narration), ver.create_date.replace('-',''), ver.create_uid.login)
            #~ str += '#VER "" %s %s "%s" %s %s\n{\n' % (ver.name, ver.date, ver.narration, ver.create_date, ver.create_uid.login)
            
            for trans in ver.line_id:
                str += '#TRANS %s {} %s %s "%s" %s %s "%s" %s\n' % (trans.account_id.code, trans.balance, trans.date.replace('-',''), self.fix_empty(trans.name), trans.quantity, trans.id, trans.partner_id.name, trans.create_uid.login)
            str += '}\n'
        
        _logger.warning('\n%s\n' % str)
        return str
    
    # if narration is null, return empty string instead of parsing to False
    @api.multi
    def fix_empty(self, narration):
        if(narration):
            return narration
        else:
            return ''
        
        ''' 
    def sietyp(self):
        return correct type. some if cases.
        Typ 1 Årssaldon. Innehåller årets ingående och utgående saldon för samtliga konton i kontoplanen
        Typ 2 Periodsaldon. Innehåller all information från typ 1 samt månadsvisa saldoförändringar för samtliga konton.
        Typ 3 Objektsaldon. Identisk med typ 2, men saldon finns även på objektnivå, t ex kostnadsställen och projekt.
        Typ 4 Transaktioner. Identisk med typ 3, men innehåller även samtliga verifikationer för räkenskapsåret. Detta filformat kan användas för export av årets grundboksnoteringar till ett program för transaktionsanalys
        Typ 4i Transaktioner. Innehåller endast verifikationer. Filformatet används när ett försystem, t ex ett löneprogram eller ett faktureringsprogram ska generera bokföringsorder för inläsning i bokföringssystemet.
        '''
