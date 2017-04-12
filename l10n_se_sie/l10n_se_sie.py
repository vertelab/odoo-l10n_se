# -*- coding: utf-8 -*-
from cStringIO import StringIO
from openerp import models, fields, api, _
from openerp.exceptions import Warning, RedirectWarning
from openerp import http
import base64
import tempfile
from werkzeug.datastructures import Headers
from werkzeug.wrappers import Response
import re
import codecs

import openerp

import logging
_logger = logging.getLogger(__name__)

class account_sie_account(models.TransientModel):
    _name = 'account.sie.account'
    _description = 'SIE Import New Account Line'
    
    @api.model
    def default_user_type(self):
        return self.env.ref('account.data_account_type_asset')
    
    wizard_id = fields.Many2one(comodel_name='account.sie', string='Wizard')
    checked = fields.Boolean(string='')
    name = fields.Char(string='Name', required=True, select=True)
    code = fields.Char(string='Code', size=64, required=True)
    type = fields.Selection(selection=[
            ('view', 'View'),
            ('other', 'Regular'),
            ('receivable', 'Receivable'),
            ('payable', 'Payable'),
            ('liquidity','Liquidity'),
            ('consolidation', 'Consolidation'),
            ('closed', 'Closed'),
        ], string='Internal Type', default='other', required=True, help="The 'Internal Type' is used for features available on "\
            "different types of accounts: view can not have journal items, consolidation are accounts that "\
            "can have children accounts for multi-company consolidations, payable/receivable are for "\
            "partners accounts (for debit/credit computations), closed for depreciated accounts.")
    user_type = fields.Many2one('account.account.type', 'Account Type', required=True, default=default_user_type,
            help="Account Type is used for information purpose, to generate "
              "country-specific legal reports, and set the rules to close a fiscal year and generate opening entries.")
    parent_id = fields.Many2one(comodel_name='account.account', string='Parent', domain=[('type','=','view')])
    
class account_sie(models.TransientModel):
    _name = 'account.sie'
    _description = 'SIE Import Wizard'

    date_start = fields.Date(string = "Date interval")
    date_stop = fields.Date(string = "Stop Date")
    period_ids = fields.Many2many(comodel_name = "account.period", string="Periods" ,) # domain="[('company_id','=',self.env.ref('base.main_company').id)]"
    fiscalyear_ids = fields.Many2one(comodel_name = "account.fiscalyear", string = "Fiscal Year",help="Moves in this fiscal years",)
    journal_ids = fields.Many2many(comodel_name = "account.journal", string = "Journal",help="Moves with this type of journals",)
    partner_ids = fields.Many2many(comodel_name = "res.partner", string="Partner",help="Moves tied to these partners",)
    account_ids = fields.Many2many(comodel_name = "account.account", string = "Account",)
    account_line_ids = fields.One2many(comodel_name='account.sie.account', inverse_name='wizard_id', string='New Accounts')
    state =  fields.Selection([('choose', 'choose'), ('get', 'get'),],default="choose")
    data = fields.Binary('File')
    filename = fields.Char(string='Filename')
    show_account_lines = fields.Boolean(string='Show Account Lines')
    
    accounts_type = fields.Selection(selection=[
            ('view', 'View'),
            ('other', 'Regular'),
            ('receivable', 'Receivable'),
            ('payable', 'Payable'),
            ('liquidity','Liquidity'),
            ('consolidation', 'Consolidation'),
            ('closed', 'Closed'),
        ], string='Internal Type', help="The 'Internal Type' is used for features available on "\
            "different types of accounts: view can not have journal items, consolidation are accounts that "\
            "can have children accounts for multi-company consolidations, payable/receivable are for "\
            "partners accounts (for debit/credit computations), closed for depreciated accounts.")
    accounts_user_type = fields.Many2one('account.account.type', 'Account Type',
            help="Account Type is used for information purpose, to generate "
              "country-specific legal reports, and set the rules to close a fiscal year and generate opening entries.")
    accounts_parent_id = fields.Many2one(comodel_name='account.account', string='Parent', domain=[('type','=','view')])
    
    @api.one
    def _data(self):
        self.sie_file = self.data
    sie_file = fields.Binary(compute='_data')
    
    @api.one
    @api.onchange('accounts_type')
    def onchange_accounts_type(self):
        for line in self.account_line_ids:
            if line.checked:
                line.type = self.accounts_type
    
    @api.one
    @api.onchange('accounts_user_type')
    def onchange_accounts_user_type(self):
        for line in self.account_line_ids:
            if line.checked:
                line.user_type = self.accounts_user_type
    
    @api.one
    @api.onchange('accounts_parent_id')
    def onchange_accounts_parent_id(self):
        for line in self.account_line_ids:
            if line.checked:
                line.parent_id = self.accounts_parent_id
    
    @api.one
    @api.onchange('data')
    def onchange_data(self):
        if self.data:
            self.check_import_file(check_periods=False)
            
    @api.model
    def cleanse_with_fire(self, data):
        data = base64.decodestring(data or '').decode('cp437')
        text_list = []
        # Clean away empty lines and carriage return. Ceterum censeo Bill Gates esse delendam.
        for line in data.split('\n'):
            line = line.strip()
            if line:
                text_list.append(line)
        data = self.read_file(text_list)
        _logger.debug(data)
        return data
    
    @api.multi
    def check_import_file(self, data=None, check_periods=True):
        self.ensure_one()
        if data or self.data: # IMPORT TRIGGERED
            checked = True
            data = data or self.cleanse_with_fire(self.data)
            missing_accounts = self.env['account.account'].check__missing_accounts(self._import_accounts(data))
            if len(missing_accounts) > 0:
                for account in missing_accounts:
                    self.account_line_ids |= self.env['account.sie.account'].create({
                            'name': account[1],
                            'code': account[0],
                        })
                    checked = False
            if check_periods:
                missing_period = self._check_periods(data)
                if missing_period:
                    raise Warning("Missing period/fiscal year for %s - %s." % (missing_period[0], missing_period[1]))
            return checked
    
    @api.multi
    def create_accounts(self):
        self.ensure_one()
        for line in self.account_line_ids:
            self.env['account.account'].create({
                    'name': line.name,
                    'code': line.code,
                    'type': line.type,
                    'user_type': line.user_type.id,
                    'parent_id': line.parent_id and line.parent_id.id or None,
                })
        self.account_line_ids = None
        self.show_account_lines = False
    
    @api.model
    def read_line(self, line, i=0):
        res = []
        field = ''
        citation = False
        escaped = False
        while i < len(line):
            if escaped:
                field += line[i]
                escaped = False
            elif line[i] == '\\':
                escaped = True
            else:
                if citation:
                    if line[i] == '"':
                        citation = False
                    else:
                        field += line[i]
                elif line[i] == '{':
                    l, i = self.read_line(line, i + 1)
                    res.append(l)
                elif line[i] == '}':
                    if field:
                        res.append(field)
                    return res, i
                elif (line[i] in (' ', '\t')):
                    if field:
                        res.append(field)
                        field = ''
                elif line[i] == '"':
                    citation = True
                else:
                    field += line[i]
            i += 1
        if field:
            res.append(field)
        return res
    
    @api.model
    def read_file(self, text_list, i = 0):
        res = []
        last_line = None
        while i < len(text_list):
            _logger.debug(i)
            if text_list[i] == '{':
                _logger.debug('down')
                l, i = self.read_file(text_list, i + 1)
                last_line['lines'] = l
            elif text_list[i] == '}':
                _logger.debug('up')
                return res, i
            else:
                l = self.read_line(text_list[i])
                _logger.debug(l)
                last_line = {}
                for x in range(len(l)):
                    if x == 0:
                        last_line['label'] = l[x]
                    else:
                        last_line[x] = l[x]
                _logger.debug(last_line)
                res.append(last_line)
            i += 1
        return res
    
    @api.multi
    def send_form(self):
        self.ensure_one()
        if self.data: # IMPORT TRIGGERED
            data = self.cleanse_with_fire(self.data)
            if not self.check_import_file(data):
                raise Warning("Import file did not pass checks! Accounts may be missing.")
            ver_ids = self._import_ver(data)
            action = self.env['ir.actions.act_window'].for_xml_id('account', 'action_move_journal_line')
            action['res_ids'] = ver_ids
            return action
            #~ {
                #~ 'type': 'ir.actions.act_window',
                #~ 'res_model': 'account.move',
                #~ 'view_mode': 'tree',
                #~ 'view_type': 'tree',
                #~ 'res_ids': ver_ids,
                #~ 'views': [(False, 'tree')],
            #~ }
        else:
            search = []
            if self.date_start:
                search.append(('date','>=',self.date_start))
                search.append(('date','<=',self.date_stop))
            if self.fiscalyear_ids:
                search.append(('period_id','in',[p.id for p in self.fiscalyear_ids.period_ids]))
            if self.period_ids:
                search.append(('period_id','in',[p.id for p in self.period_ids]))
            if self.journal_ids:
                search.append(('journal_id','in',[j.id for j in self.journal_ids]))
            if self.partner_ids:
                search.append(('partner_id','in',[p.id for p in self.partner_ids]))
            move_ids = self.env['account.move'].search(search)
            if self.account_ids:
                accounts = [l.move_id.id for l in self.env['account.move.line'].search([('account_id','in',[a.id for a in self.account_ids])])]
                move_ids = move_ids.filtered(lambda r: r.id in accounts)
            self.write({'state': 'get', 'data': base64.encodestring(self.make_sie(move_ids)),'filename': 'filename.sie4' })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.sie',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
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

        if not company.company_registry:
            raise Warning("Please configure company registry!")

        str = ''
        str += '#FLAGGA 0\n'
        str += '#PROGRAM "Odoo" %s\n' % openerp.service.common.exp_version()['server_serie']
        str += '#FORMAT PC8\n' # ,Anger vilken teckenuppsattning som anvants
        str += '#GEN %s\n'% fields.Date.today().replace('-','')
        str += '#SIETYP 4i\n'
        for fiscalyear in get_fiscalyears(ver_ids):
            str += '#RAR %s %s %s\n' %(fiscalyear.get_rar_code(), fiscalyear.date_start.replace('-',''), fiscalyear.date_stop.replace('-',''))
        str += '#FNAMN %s\n' %company.name
        str += '#ORGNR %s\n' %company.company_registry
        str += '#ADRESS "%s" "%s" "%s %s" "%s"\n' %(user.display_name, company.street, company.zip, company.city, company.phone)
        str += '#KPTYP %s\n' %(company.kptyp if company.kptyp else 'BAS2015')
        for account in get_accounts(ver_ids):
            str += '#KONTO %s "%s"\n' % (account.code, account.name)

        #raise Warning("str: %s %s search:%s" % (str, self.env['account.move.line'].search(search),search))

        #TRANS  kontonr {objektlista} belopp  transdat transtext  kvantitet   sign
        #VER    serie vernr verdatum vertext regdatum sign

        for ver in ver_ids:
            
            if ver.period_id.special == False:
            
                str += '#VER %s %s %s "%s" %s\n{\n' % (ver.journal_id.type,ver.name, ver.date.replace('-',''), self.fix_empty(ver.narration), ver.create_uid.login)
                #~ str += '#VER "" %s %s "%s" %s %s\n{\n' % (ver.name, ver.date, ver.narration, ver.create_date, ver.create_uid.login)

                for trans in ver.line_id:
                    str += '#TRANS %s {} %s %s "%s" %s %s\n' % (trans.account_id.code, trans.debit - trans.credit, trans.date.replace('-',''), self.fix_empty(trans.name), trans.quantity, trans.create_uid.login)
                str += '}\n'

            else:  #IB
                for trans in ver.line_id:
                    str += '#IB %s %s %s' % (fiscalyear.get_rar_code(),trans.account_id.code,trans.debit - trans.credit)
                
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

    def _import_accounts(self, data):
        list_of_accounts = []
        accounts = []
        for line in data:
            if line['label'] == '#KONTO':
                _logger.debug(line)
                accounts.append((line[1], line[2]))
        return accounts
    
    def _check_periods(self, data):
        missing_period = []
        for line in data:
            if line['label'] == '#VER':
                try:
                    self.env['account.period'].find(dt=line[3])
                except RedirectWarning:
                    if not missing_period:
                        missing_period = [line[3], line[3]]
                    elif line[3] < missing_period[0]:
                        missing_period[0] = line[3]
                    elif line[3] > missing_period[1]:
                        missing_period[1] = line[3]
        return missing_period
    
    @api.multi
    def _import_ver(self, data):
        self.ensure_one()
        journal_types = []
        ver_ids = []
        for line in data:
            if line['label'] == '#VER':
                list_date = line.get(3)  # date
                list_ref = line.get(2)   # reference
                list_sign = line.get(5)  # sign
                
                #VER A 1 20091101 "" 20091202 "2 Christer Bengtsson"
                #VER "" BNK2/2016/0001 20160216 "" admin
                
                if self.env['account.journal'].search([('type', '=', line[1]), ('company_id', '=', self.env.ref('base.main_company').id)]):  # Serial are a journal
                        journal_type = line[1]
                elif [j for j in ['sale', 'sale_refund', 'purchase', 'purchase_refund'] if j in journal_types]:
                    journal_type = [j for j in ['sale', 'sale_refund', 'purchase', 'purchase_refund'] if j in journal_types][0]
                elif [j for j in ['bank', 'cash'] if j in journal_types]:
                    journal_type = [j for j in ['bank', 'cash'] if j in journal_types][0]
                else:
                    journal_type = 'general'
                
                ver_id = self.env['account.move'].create({
                    'period_id': self.env['account.period'].find(dt=list_date).id,
                    'journal_id': self.env['account.journal'].search([('type', '=', journal_type), ('company_id', '=', self.env.ref('base.main_company').id)])[0].id,
                    #'journal_id': self.env['account.journal'].search([('type','=','general'),('company_id','=',self.env.ref('base.main_company').id)])[0].id,
                    })
                ver_ids.append(ver_id.id)
                
                
                #~ #VER "" SAJ/2016/0002 20150205 "" admin
                #~ {
                #~ #TRANS kontonr   {objektlista}   belopp transdat transtext   kvantitet   sign
                #~ #TRANS 1510      {}              -100.0 20150205 "/"         1.0         admin
                #~ #TRANS 2610 {} 0.0 20150205 "Försäljning 25%" 1.0 admin
                #~ #TRANS 3000 {} 0.0 20150205 "Skor" 1.0 admin
                #~ }
                for l in line.get('lines', []):
                    if l['label'] == '#TRANS':
                        trans_code = l[1]
                        trans_object = l[2]
                        trans_balance = l[3]
                        trans_name = '#'
                        trans_date = l.get(4)
                        trans_name = l.get(5)
                        trans_quantity = l.get(6)
                        trans_sign = l.get(7)
                        # Seems to not be used.
                        #~ user = self.env['res.users'].search([('login', '=', trans_sign)]) if trans_sign else None
                        code = self.env['account.account'].search([('code', '=', trans_code),('company_id', '=', self.env.ref('base.main_company').id)], limit=1)
                        
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
                        period_id = self.env['account.period'].find(dt=list_date).id
                        _logger.debug('\naccount_id :%s\nbalance: %s\nperiod_id: %s' %(code, trans_balance, period_id))

                        trans_id = self.env['account.move.line'].create({
                            'account_id': code.id,
                            'credit': float(trans_balance) < 0 and float(trans_balance) * -1 or 0.0,
                            'debit': float(trans_balance) > 0 and float(trans_balance) or 0.0,
                            'period_id': period_id,
                            'date': '' + trans_date[0:4] + '-' + trans_date[4:6] + '-' + trans_date[6:],
                            #'quantity': trans_quantity,
                            'name': trans_name,
                            'move_id': ver_id.id,
                            })
        return ver_ids
