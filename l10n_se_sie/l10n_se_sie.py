# -*- coding: utf-8 -*-
from cStringIO import StringIO
from openerp import models, fields, api, _
from openerp.exceptions import Warning
from openerp import http
import base64
import tempfile
from werkzeug.datastructures import Headers
from werkzeug.wrappers import Response
import re

import openerp

import logging
_logger = logging.getLogger(__name__)

class account_sie(models.TransientModel):
    _name = 'account.sie'
    _description = 'Odoo'
       
    date_start = fields.Date(string = "Date interval")
    date_stop = fields.Date(string = "Stop Date")
    period_ids = fields.Many2many(comodel_name = "account.period", string="Periods" ,) # domain="[('company_id','=',self.env.ref('base.main_company').id)]"
    fiscalyear_ids = fields.Many2one(comodel_name = "account.fiscalyear", string = "Fiscal Year",help="Moves in this fiscal years",)
    journal_ids = fields.Many2many(comodel_name = "account.journal", string = "Journal",help="Moves with this type of journals",)
    partner_ids = fields.Many2many(comodel_name = "res.partner", string="Partner",help="Moves tied to these partners",)
    account_ids = fields.Many2many(comodel_name = "account.account", string = "Account",)
    
    state =  fields.Selection([('choose', 'choose'), ('get', 'get'),],default="choose") 
    data = fields.Binary('File')
    filename = fields.Char(string='Filename')
    @api.one
    def _data(self):
        self.sie_file = self.data
    sie_file = fields.Binary(compute='_data')

        
    @api.multi
    def send_form(self,):
        sie_form = self[0]
        #raise Warning('Hello %s %s %s' % (base64.decodestring(sie_form.data or ''),self,self.state))
        _logger.warning('Hello %s %s %s' % (base64.decodestring(sie_form.data or ''),self,self.filename))
        if not sie_form.data == None: # IMPORT TRIGGERED
            sie_file = base64.decodestring(sie_form.data)            
            missing_accounts = self.env['account.account'].check__missing_accounts(self._import_accounts(sie_file))
            if len(missing_accounts) > 0:
                raise Warning(_('Accounts missing, add before import\n%s') % '\n '.join(['%s %s' %(a[0],_(a[1])) for a in missing_accounts]))
            self._import_ver(sie_file)
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_mode': 'tree',
                'view_type': 'tree',
                #~ 'res_id': sie_form.id,
                'views': [(False, 'tree')],
            }
        else:    
            search = []
            if sie_form.date_start:
                search.append(('date','>=',sie_form.date_start))
                search.append(('date','<=',sie_form.date_stop))
            if sie_form.fiscalyear_ids:
                search.append(('period_id','in',[p.id for p in sie_form.fiscalyear_ids.period_ids]))
            if sie_form.period_ids:
                search.append(('period_id','in',[p.id for p in sie_form.period_ids]))
            if sie_form.journal_ids:
                search.append(('journal_id','in',[j.id for j in sie_form.journal_ids]))
            if sie_form.partner_ids:
                search.append(('partner_id','in',[p.id for p in sie_form.partner_ids]))
            move_ids = self.env['account.move'].search(search)
            if sie_form.account_ids:
                accounts = [l.move_id.id for l in self.env['account.move.line'].search([('account_id','in',[a.id for a in sie_form.account_ids])])]
                move_ids = move_ids.filtered(lambda r: r.id in accounts)
            sie_form.write({'state': 'get', 'data': base64.encodestring(self.make_sie(move_ids)),'filename': 'filename.sie4' })
        
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
    def make_sie(self, ver_ids):
    
        def get_fiscalyears(ver_ids):
            year_list = set()
            for ver in ver_ids:
                year_list.add(ver.period_id.fiscalyear_id)
            return year_list
        def get_accounts(ver_ids):
            account_list = set()
            for ver in ver_ids:
                for line in ver.line_id:
                #for l in ver.line_id for ver in ver_ids]]:
                    account_list.add(line.account_id)
            return account_list        
                
        if len(self) > 0:
            sie_form = self[0]
        
        company = ver_ids[0].company_id
        fiscalyear = ver_ids[0].period_id.fiscalyear_id
        user = self.env['res.users'].browse(self._context['uid'])

        str = ''
        str += '#FLAGGA 0\n' 
        str += '#PROGRAM "Odoo" %s\n' % openerp.service.common.exp_version()['server_serie']
        str += '#FORMAT PC8\n' # ,Anger vilken teckenuppsattning som anvants
        str += '#GEN %s\n'% fields.Date.today().replace('-','')
        str += '#SIETYP 4i\n'
        for fiscalyear in get_fiscalyears(ver_ids):
            str += '#RAR %s %s %s\n' %(fiscalyear.get_rar_code(), fiscalyear.date_start.replace('-',''), fiscalyear.date_stop.replace('-',''))
        str += '#ORGNR %s\n' %company.company_registry
        str += '#ADRESS "%s" "%s" "%s %s" "%s"\n' %(user.display_name, company.street, company.zip, company.city, company.phone)
        str += '#KPTYP %s\n' % company.kptyp or 'BAS2015'
        for account in get_accounts(ver_ids):
            str += '#KONTO %s "%s"\n' % (account.code, account.name)
            
        #raise Warning("str: %s %s search:%s" % (str, self.env['account.move.line'].search(search),search))  
        
        #TRANS  kontonr {objektlista} belopp  transdat transtext  kvantitet   sign
        #VER    serie vernr verdatum vertext regdatum sign
    
        for ver in ver_ids:
            str += '#VER %s %s %s "%s" %s\n{\n' % (ver.journal_id.type,ver.name, ver.date.replace('-',''), self.fix_empty(ver.narration), ver.create_uid.login)
            #~ str += '#VER "" %s %s "%s" %s %s\n{\n' % (ver.name, ver.date, ver.narration, ver.create_date, ver.create_uid.login)
            
            for trans in ver.line_id:
                str += '#TRANS %s {} %s %s "%s" %s %s\n' % (trans.account_id.code, trans.balance, trans.date.replace('-',''), self.fix_empty(trans.name), trans.quantity, trans.create_uid.login)
            str += '}\n'
        
        _logger.warning('\n%s\n' % str)
        
        return str.encode('ascii','xmlcharrefreplace') # ignore
    
    @api.model
    def export_sie(self,ver_ids):
        if len(self) < 1:
            sie_form = self.create({})
        else:
            sie_form=self[0]
        _logger.info('export: %s' % ver_ids)
        sie_form.write({'state': 'get', 'data': base64.b64encode(sie_form.make_sie(ver_ids)) ,'filename': 'filename.sie4' })
        view = self.env.ref('l10n_se_sie.wizard_account_sie', False)
        _logger.info('view %s sie_form %s %s %s' % (view,sie_form,sie_form.sie_file,base64.b64encode(sie_form.make_sie(ver_ids))))
        #~ sie_form.write({'state': 'get', 'data': base64.b64encode(self.make_sie()) })
        return {
            'name': _('SIE-export'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.sie',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': sie_form.id,
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
        }
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
    @api.multi
    def import_sie(self):
        sie_form = self[0]
        raise Warning(sie_form.data)
        #~ result = {}
        #~ for product_data in self.browse(cr, uid, ids, context=context):
                #~ result[product_data.id] = product_data['file_path']
                #~ return result
        #~ return result

        #_logger.warning('\n%s' % base64.encodestring(args.get('data').read()))
        
    def _stringSplit(self, string):
        tempString = ""
        splitList = []
        quote = False
        for s in range(0, len(string)):
            if (not quote and string[s] == '"'):
                quote = True
                tempString += string[s]
            elif (quote and string[s] == '"'):
                quote = False
                tempString += string[s]
                if (len(tempString) > 0):
                    splitList.append(tempString)
                tempString = ""
            elif (quote and string[s] == ' '):
                tempString += string[s]
            elif (not quote and string[s] == ' '):
                if (len(tempString) > 0):
                    splitList.append(tempString)
                tempString = ""
            elif (not quote and s == len(string)-1 and not string[s] == ' '):
                tempString += string[s]
                splitList.append(tempString)
            else:
                tempString += string[s]
        return splitList
    
    def _import_accounts(self, string):
        list_of_accounts = []
        accounts = []
        for account in re.finditer(re.compile(r'(#KONTO .+)+', re.MULTILINE), string):
            list_of_accounts.append(account.group())
        for x in (list_of_accounts):
            tmpvar = self._stringSplit(x)
            accounts.append((tmpvar[1],tmpvar[2]))
        return accounts
    
    def _import_ver(self,string):
        # ^#(.+?)\s+(.+?)\s+(.+?)\s+(.+?)\s+\"(.+?)\"(.+?)\s+\"(.+?)\"
        for ver in re.finditer(re.compile(r'#VER .+\n{\n(#TRANS .+\n)+}\n', re.MULTILINE), string.decode('utf-8','xmlcharrefreplace')):
            verString = '' + (re.search(re.compile(r'#VER .+'),ver.group()).group())
            verList = self._stringSplit(verString)
            list_date = verList[3]  # date
            list_ref = verList[2]   # reference
            list_sign = verList[5]  # sign
            if not self.env['account.period'].find(dt=list_date):
                raise Warning("Missing period/fiscal year for %s " % list_date)
            
#VER A 1 20091101 "" 20091202 "2 Christer Bengtsson"
#VER "" BNK2/2016/0001 20160216 "" admin
            ver_id = self.env['account.move'].create({
                'period_id': self.env['account.period'].find(dt=list_date).id,
                'journal_id': self.env['account.journal'].search([('type','=','general'),('company_id','=',self.env.ref('base.main_company').id)])[0].id,
                })
            _logger.warning('VER %s' %ver_id)
                

#~ #VER "" SAJ/2016/0002 20150205 "" admin
#~ {
#~ #TRANS kontonr   {objektlista}   belopp transdat transtext   kvantitet   sign
#~ #TRANS 1510      {}              -100.0 20150205 "/"         1.0         admin
#~ #TRANS 2610 {} 0.0 20150205 "Försäljning 25%" 1.0 admin
#~ #TRANS 3000 {} 0.0 20150205 "Skor" 1.0 admin
#~ }

            journal_types = []
            for trans in re.findall(re.compile('#TRANS .+'),ver.group()):
                transList = self._stringSplit(trans)
                args = len(transList)
                # these should always be set args <= 4
                trans_code = transList[1]
                trans_object = transList[2]
                trans_balance = transList[3]
                trans_name = '#'
                if args >=5:
                    trans_date = transList[4]
                if args >= 6:
                    trans_name = transList[5]
                if args >= 7:
                    trans_quantity = transList[6]
                
                trans_sign = transList[len(transList)-1]
                user = self.env['res.users'].search([('login','=',trans_sign)])
                if user:
                    user = user[0].id
                else:
                    user = None
                
                code = self.env['account.account'].search([('code','=',trans_code),('company_id','=',self.env.ref('base.main_company').id)],limit=1)
                
            
                #~ 3000 regular  report_type income  balance > 0 -> sale balance < 0 -> sale_refund  ( user_type data_account_type_income + balance > 0)
                #~ 1210  report_type = asset
                #~ 5400  report_type = expense  purchase / purchase_refund
                #~ 1500 Receivable
                #~ 1932 Liquidity -> report_type -> asset
                #~ 1910 Liquidity -> user_type  = ref('account.data_account_type_bank')  -> bank
                #~ 1932 Liquidity -> user_type  = ref('account.data_account_type_cash')  -> cash

                if code.user_type.report_type == 'income':
                    journal_types.append('sale' and float(trans_balance) > 0.0 or 'sale_refund')
                elif code.user_type.id == self.env.ref('account.data_account_type_bank').id:
                    journal_types.append('bank')
                elif code.user_type.id == self.env.ref('account.data_account_type_cash').id:
                    journal_types.append('cash')
                elif code.user_type.report_type in ['asset','expense']:
                    journal_types.append('purchase' and float(trans_balance) > 0.0 or 'purchase_refund')
                                
                #~ raise Warning(self.env['account.move.line'].search([])[0].date)
                _logger.warning('\naccount_id :%s\nbalance: %s\nperiod_id: %s' %(code,trans_balance,self.env['account.period'].find(dt=list_date).id))

                trans_id = self.env['account.move.line'].create({
                    'account_id': code.id,
                    'credit': float(trans_balance) < 0 and float(trans_balance) * -1 or 0.0,
                    'debit': float(trans_balance) > 0 and float(trans_balance) or 0.0,
                    'period_id': self.env['account.period'].find(dt=list_date).id,
                    'date': '' + trans_date[0:4] + '-' + trans_date[4:6] + '-' + trans_date[6:],
                    #'quantity': trans_quantity,
                    'name': trans_name,
                    'move_id': ver_id.id,
                    })
        
            if self.env['account.journal'].search([('type','=',verList[1]),('company_id','=',self.env.ref('base.main_company').id)]):  # Serial are a journal
                journal_type = verList[1]
            elif [j for j in ['sale','sale_refund','purchase','purchase_refund'] if j in journal_types]:
                journal_type = [j for j in ['sale','sale_refund','purchase','purchase_refund'] if j in journal_types][0]
            elif [j for j in ['bank','cash'] if j in journal_types]:
                journal_type = [j for j in ['bank','cash'] if j in journal_types][0]
            else:
                journal_type = 'general'
            ver_id.write({'journal_id': self.env['account.journal'].search([('type','=',journal_type),('company_id','=',self.env.ref('base.main_company').id)])[0].id})
