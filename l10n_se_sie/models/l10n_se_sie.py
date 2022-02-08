# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import Warning, RedirectWarning
from odoo import http
import base64
from datetime import datetime
import odoo

import logging
_logger = logging.getLogger(__name__)


class account_sie_account(models.TransientModel):
    _name = 'account.sie.account'
    _description = 'SIE Import New Account Line'

    @api.model
    def default_user_type(self):
        # ~ return self.env.ref('account.data_account_type_asset')
        # data_account_type_current_assets
        # data_account_type_fixed_assets
        return self.env.ref('account.data_account_type_fixed_assets')
    wizard_id = fields.Many2one(comodel_name='account.sie', string='Wizard')
    checked = fields.Boolean(string='')
    reconcile = fields.Boolean(string='')
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

    debug = fields.Boolean(default = False)                            #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! SET TO FALSE WHEN DEPLOYED IF SET TO TRUE THEN THIS FILE WILL CREATE THE MISSING ACCOUNTS AND DO THAT BADLY
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
    move_journal_id = fields.Many2one(comodel_name = "account.journal", string = "Journal", help="All imported account.moves will get this journal",)

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

    def _get_rar_code(self, fy):
        self.ensure_one()
        i = 0
        for year in self.fiscalyear_ids.sorted(lambda r: r.date_start, reverse=False):
            if fy == year:
                return i
            i += 1
        return i
        # raise Warning("Couldn't get RAR code.")


    def _data(self):
        self.sie_file = self.data
    sie_file = fields.Binary(compute='_data')

    # ~ @api.one
    # ~ @api.onchange('accounts_type')
    # ~ def onchange_accounts_type(self):
        # ~ for line in self.account_line_ids:
            # ~ if line.checked:
                # ~ line.type = self.accounts_type

    # ~ @api.one
    # ~ @api.onchange('accounts_user_type')
    # ~ def onchange_accounts_user_type(self):
        # ~ for line in self.account_line_ids:
            # ~ if line.checked:
                # ~ line.user_type = self.accounts_user_type

    # ~ @api.one
    # ~ @api.onchange('accounts_parent_id')
    # ~ def onchange_accounts_parent_id(self):
        # ~ for line in self.account_line_ids:
            # ~ if line.checked:
                # ~ line.parent_id = self.accounts_parent_id

    # ~ @api.one
    # ~ @api.onchange('data')
    # ~ def onchange_data(self):
        # ~ if self.data:
            # ~ self.check_import_file(check_periods=False)

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

    def check_import_file(self, data=None, check_periods=True):
        self.ensure_one()
        if data or self.data: # IMPORT TRIGGERED
            checked = True
            data = data or self.cleanse_with_fire(self.data)
            missing_accounts = self.env['account.account'].check__missing_accounts(self._import_accounts(data))
            if len(missing_accounts) > 0:
                # ~ for account in missing_accounts:
                    # ~ self.account_line_ids |= self.env['account.sie.account'].create({
                            # ~ 'name': account[1],
                            # ~ 'code': account[0],
                        # ~ })
                    checked = False
            if check_periods:
                missing_period = self._check_periods(data)
                if missing_period:
                    raise Warning("Missing period/fiscal year for %s - %s." % (missing_period[0], missing_period[1]))
            return checked

    def create_accounts(self):
        self.ensure_one()
        for line in self.account_line_ids:
            self.env['account.account'].create({
                    'name': line.name,
                    'code': line.code,
                    'internal_type': line.type,
                    'user_type_id': line.user_type.id,
                    'root_id': line.parent_id and line.parent_id.id or None,
                    'reconcile':line.reconcile,
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

    def send_form(self):
        self.ensure_one()

        if self.data: # IMPORT TRIGGERED
            if not self.move_journal_id:
                raise Warning(f"Please select a journal")
            data = self.cleanse_with_fire(self.data)
            if not self.check_import_file(data):
                missing_accounts = self.env['account.account'].check__missing_accounts(self._import_accounts(data))
                formatstring = ""
                for account in missing_accounts:
                    formatstring += account[0] + ": "  + account[1] + "\n"
                    if self.debug:
                        self.env["account.account"].create({
                            "code": account[0] ,
                            "name": account[1],
                            "reconcile":True,
                            "user_type_id":self.env.ref('account.data_account_type_non_current_assets').id,
                        })
                if not self.debug:
                    raise Warning(f"Import file did not pass checks! Accounts may be missing. \n{formatstring}")
                else:
                    _logger.warning(f"Import file did not pass checks! Accounts may be missing. Creating if you see this in the log on a production server then I done goofed \n{formatstring}")

                    # ~ return {
                    # ~ 'warning': {'title': _('Error'), 'message': _('Import file did not pass checks! Accounts may be missing.'),},
                # ~ }
            ver_ids = self._import_ver(data)
            action = self.env['ir.actions.act_window']._for_xml_id('account.action_move_journal_line')
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
        
            self.write({'state': 'get', 'data': base64.encodestring(self.make_sie(move_ids)),'filename': 'filename.se' })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.sie',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }

    def make_sie(self, ver_ids):
        def get_fiscalyears(ver_ids):
            year_list = set()
            for ver in ver_ids:
                year_list.add(ver.period_id.fiscalyear_id)
            return year_list
        def get_accounts(ver_ids):
            return list(set(ver_ids.mapped('line_ids.account_id')))

        if len(self) > 0:
            sie_form = self[0]
        if len(ver_ids) == 0:
            raise Warning('There are no entries for this selection, please do antoher')
        company = ver_ids[0].company_id
        fiscalyear = ver_ids[0].period_id.fiscalyear_id
        user = self.env['res.users'].browse(self._context['uid'])
        #if not company.company_registry:
        #    raise Warning("Please configure company registry!")
        str = ''
        str += '#FLAGGA 0\n'
        str += '#PROGRAM "Odoo" %s\n' % odoo.service.common.exp_version()['server_serie']
        str += '#FORMAT PC8\n' # ,Anger vilken teckenuppsattning som anvants
        # ~ str += '#GEN %s\n'% fields.Date.today().replace('-','')
        str += '#GEN %s\n'%  fields.Date.today().strftime("%Y%m%d")
        str += '#SIETYP 4\n'
        for fiscalyear in get_fiscalyears(ver_ids):
            # ~ str += '#RAR %s %s %s\n' %(self._get_rar_code(fiscalyear), fiscalyear.date_start.replace('-',''), fiscalyear.date_stop.replace('-',''))
            str += '#RAR %s %s %s\n' %(self._get_rar_code(fiscalyear), fiscalyear.date_start.strftime("%Y%m%d"), fiscalyear.date_stop.strftime("%Y%m%d"))
        str += '#FNAMN "%s"\n' %company.name
        str += '#ORGNR %s\n' %company.company_registry
        str += '#ADRESS "%s" "%s" "%s %s" "%s"\n' %(user.display_name, company.street, company.zip, company.city, company.phone)
        str += '#KPTYP %s\n' %(company.kptyp if company.kptyp else 'BAS2015')
        for account in get_accounts(ver_ids):
            str += '#KONTO %s "%s"\n' % (account.code, account.name)

        #raise Warning("str: %s %s search:%s" % (str, self.env['account.move.line'].search(search),search))

        #TRANS  kontonr {objektlista} belopp  transdat transtext  kvantitet   sign
        #VER    serie vernr verdatum vertext regdatum sign
        # We seem to not add a regdatum which some parser don't agree with since we add the sign field
        _logger.warning("BEFORE GOING TROUGH ALL VER")
        ub = {}
        ub_accounts = []
        for ver in ver_ids:
            _logger.warning(f"{ver=}")
            if ver.period_id.special == False:
                str += '#VER %s "%s" %s "%s" %s %s\n{\n' % (self.escape_sie_string(ver.journal_id.type), ver.id, self.escape_sie_string(ver.date.strftime("%Y%m%d")), self.escape_sie_string(self.fix_empty(ver.narration))[:20], self.escape_sie_string(ver.create_date.strftime("%Y%m%d")),self.escape_sie_string(ver.create_uid.login))
                # ~ str += '#VER %s "%s" %s "%s" %s\n{\n' % (self.escape_sie_string(ver.journal_id.type), ver.id, self.escape_sie_string(ver.date.strftime("%Y%m%d")), self.escape_sie_string(self.fix_empty(ver.narration))[:20], self.escape_sie_string(ver.create_uid.login))
                #~ str += '#VER %s "%s" %s "%s" %s\n{\n' % (self.escape_sie_string(ver.journal_id.type), self.escape_sie_string('' if ver.name == '/' else ver.name), self.escape_sie_string(ver.date.replace('-','')), self.escape_sie_string(self.fix_empty(ver.narration)), self.escape_sie_string(ver.create_uid.login))
                #~ str += '#VER "" %s %s "%s" %s %s\n{\n' % (ver.name, ver.date, ver.narration, ver.create_date, ver.create_uid.login)
                for trans in ver.line_ids:
                    str += '#TRANS %s {} %s %s "%s" %s %s\n' % (self.escape_sie_string(trans.account_id.code), trans.debit - trans.credit, self.escape_sie_string(trans.date.strftime("%Y%m%d")), self.escape_sie_string(self.fix_empty(trans.name)), trans.quantity, self.escape_sie_string(trans.create_uid.login))
                    if trans.account_id.code not in ub:
                        ub[trans.account_id.code] = 0.0
                    ub[trans.account_id.code] += trans.debit - trans.credit
                str += '}\n'
            else:  #IB
                for trans in ver.line_ids:
                    #_logger.warning(f"{trans=}")
                    str += '#IB %s %s %s\n' % (self._get_rar_code(fiscalyear), self.escape_sie_string(trans.account_id.code), trans.debit - trans.credit)
                    ub_accounts.append(trans.account_id.code)
        for account in ub:
            if account in ub_accounts:
                str += '#UB %s %s %s\n' % (self._get_rar_code(fiscalyear), self.escape_sie_string(account), ub.get(account, 0.0))
            else:
                #TODO: account.code can contain whitespace and should be handled as such here and elsewhere.
                #account.user_type.report_type in ('income', 'expense') => resultatkonto
                #account.user_type.report_type in ('assets', 'liability') => balanskonto
                str += '#RES %s %s %s\n' % (self._get_rar_code(fiscalyear), self.escape_sie_string(account), ub.get(account, 0.0))

        return str.encode('cp437','xmlcharrefreplace') # ignore

    @api.model
    def escape_sie_string(self, s):
        return s.replace('\n', ' ').replace('\\', '\\\\').replace('"', '\\"')

    @api.model
    def export_sie(self,ver_ids):
        if len(self) < 1:
            sie_form = self.create({})
        else:
            sie_form=self[0]
        _logger.info('export: %s' % ver_ids)
        result = sie_form.make_sie(ver_ids)
        filetest = base64.b64encode(result)
        sie_form.write({'state': 'get', 'data': base64.b64encode(sie_form.make_sie(ver_ids)) ,'filename': 'filename.se' })
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
                #During the process of reading the example file we sometimes don't have a value in index 2. This happens when a line in the example file looks like this ' #KONTO 3019 "" '
                if len(line) < 3:
                    accounts.append((line[1], ""))
                else:
                    accounts.append((line[1], line[2]))
        return accounts

    def _check_periods(self, data):
        missing_period = []
        for line in data:
            if line['label'] == '#VER':
                try:
                    # ~ _logger.warning(f"WHAT: {self.env['account.period'].search([], limit=1)}")
                    #self.env['account.period'].find(dt=line[3]) #Expected singleton
                    self.env['account.period'].search([], limit=1).find(dt=line[3]) #The find method has self.ensure_one, which is why i find one record.
                except RedirectWarning:
                    if not missing_period:
                        missing_period = [line[3], line[3]]
                    elif line[3] < missing_period[0]:
                        missing_period[0] = line[3]
                    elif line[3] > missing_period[1]:
                        missing_period[1] = line[3]
        return missing_period

    def _import_ver(self, data):
        self.ensure_one()
        journal_types = []
        ver_ids = []

        tag_table = {}

        for line in data:
            if line['label'] == '#VER':
                
                list_date = line.get(3)  # date
                list_ref = line.get(1) + ' ' + line.get(2) + ' ' + line.get(4)  # reference
                list_sign = line.get(5)  # sign
                list_regdatum = line.get(5)  # created_date
                
                #OBLIGATORY
                #[label],[1]        ,[2]       ,[3]
                #VER    , serie    ,vernr  ,verdatum 
                
                #VOLONTARY
                #[4]        ,[5]             ,[6]
                #vertext ,regdatum ,sign
                
                
                
                
                #VER RV 155 20200914 "PAYPAL *UPWRKESCROW    35314369001   SWE, SE"

                #VER A 1 20091101 "" 20091202 "2 Christer Bengtsson"
                #VER "" BNK2/2016/0001 20160216 "" admin

                #SMART WAY OF SELECTING JOURNALS, NEED TO PLAN EXACLTY HOW THIS WORKS, ATM WE SELECT THE JOURNAL IN THE WIZARD
                # ~ if self.env['account.journal'].search([('type', '=', line[1]), ('company_id', '=', self.env.ref('base.main_company').id)]):  # Serial are a journal
                        # ~ journal_type = line[1]
                # ~ elif [j for j in ['sale', 'sale_refund', 'purchase', 'purchase_refund'] if j in journal_types]:
                    # ~ journal_type = [j for j in ['sale', 'sale_refund', 'purchase', 'purchase_refund'] if j in journal_types][0]
                # ~ elif [j for j in ['bank', 'cash'] if j in journal_types]:
                    # ~ journal_type = [j for j in ['bank', 'cash'] if j in journal_types][0]
                # ~ else:
                    # ~ journal_type = 'general'
                # ~ move_journal_id = self.env['account.journal'].search([('type', '=', journal_type), ('company_id', '=', self.env.ref('base.main_company').id)])[0].id

                move_journal_id = self.move_journal_id.id
                ver_id = self.env['account.move'].create({
                    'period_id': self.env['account.period'].search([],limit = 1).find(dt=list_date).id,
                    'journal_id': move_journal_id,
                    'date': list_date[0:4] + '-' + list_date[4:6] + '-' + list_date[6:],
                    'ref': list_ref,
                    #'journal_id': self.env['account.journal'].search([('type','=','general'),('company_id','=',self.env.ref('base.main_company').id)])[0].id,
                    })
                
                # This should maybe be changed so that the create date is the date when we created the record instead of us using the regdate from the import file
                if list_regdatum:
                    formated_create_date = list_regdatum[0:4] + '-' + list_regdatum[4:6] + '-' + list_regdatum[6:]
                    self.env.cr.execute(
                    """
                    UPDATE account_move SET create_date  = %s
                    WHERE id = %s
                    """,
                    (formated_create_date, ver_id.id),
                    )
                    _logger.warning(f"ver_id.create_date = {ver_id.create_date}")
                
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
                        trans_object = [(l[2][i*2], l[2][i*2+1]) for i in range(int(len(l[2])/2))]
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

                        if code.user_type_id.report_type == 'income':
                            journal_types.append('sale' and float(trans_balance) > 0.0 or 'sale_refund')
                        elif code.user_type_id.id == self.env.ref('account.data_account_type_liquidity').id: #changed from data_account_type_bank to data_account_type_liquidity
                            journal_types.append('bank')
                        elif code.user_type_id.id == self.env.ref('account.data_account_type_liquidity').id: #changed from data_account_type_bank to data_account_type_liquidity
                            journal_types.append('cash')
                        elif code.user_type_id.report_type in ['asset','expense']:
                            journal_types.append('purchase' and float(trans_balance) > 0.0 or 'purchase_refund')

                        #~ raise Warning(self.env['account.move.line'].search([])[0].date)
                        period_id = self.env['account.period'].search([],limit=1).find(dt=list_date).id
                        _logger.debug('\naccount_id :%s\nbalance: %s\nperiod_id: %s' %(code, trans_balance, period_id))

                        if trans_date:
                            formated_date = trans_date[0:4] + '-' + trans_date[4:6] + '-' + trans_date[6:]
                        else:
                            formated_date = ver_id.date

                        tags = []
                        tag_model = self.env['account.analytic.tag']
                        for tag_type, tag_val in trans_object:
                            tag_name_prefix = f"{tag_val} %"   # Equivalent to 'regex': "^{tag_val} .*$"
                            if tag_name_prefix not in tag_table:
                                matching_tag = tag_model.search([('name', '=like', tag_name_prefix)])
                                if len(matching_tag) == 0:
                                    raise Warning(f"Missing tag for {'project' if tag_type == '6' else 'cost center'} {tag_val}")
                                if len(matching_tag) > 1:
                                    raise Warning(f"Too many tags matching {'project' if tag_type == '6' else 'cost center'} {tag_val}")
                                tag_table[tag_name_prefix] = matching_tag.id

                            tags.append((4, tag_table[tag_name_prefix], 0))

                        line_vals = {
                            'account_id': code.id,
                            'credit': float(trans_balance) < 0 and float(trans_balance) * -1 or 0.0,
                            'debit': float(trans_balance) > 0 and float(trans_balance) or 0.0,
                            'analytic_tag_ids': tags,
                            #'period_id': period_id,
                            'date': formated_date,
                            #'quantity': trans_quantity,
                            'name': trans_name,
                            'move_id': ver_id.id,
                            }
                            
                        context_copy = self.env.context.copy()
                        context_copy.update({'check_move_validity':False})
                        trans_id = self.with_context(context_copy).env['account.move.line'].create(line_vals)
                        self.with_context(context_copy).env['account.move.line'].browse(trans_id.id)._compute_analytic_account_id()
                        
            elif line['label'] == '#IB':
            #elif line['label'] == "implment later":
                        #IB 0 1510 269174.65
                        #IB årsnr konto saldo kvantitet

                        year_num = int(line.get(1)) #Opening period for current fiscal year 
                        first_date_of_year = '%s-01-01' % (datetime.today().year + year_num)
                        period_id = self.env['account.period'].search([('date_start', '=', first_date_of_year), ('date_stop', '=', first_date_of_year), ('special', '=', True)]).id
                        _logger.warning(f"{period_id=}")
                        period_record = self.env["account.period"].browse(period_id)
                        _logger.warning(f"{period_record.date_start}")
                        ib_account = self.env['account.account'].search([('code','=',line.get(2))])
                        ib_amount = line.get(3)
                        qnt = line.get(4) # We already have a amount, what is the purpose of having a quantity as well
                        
                        move_journal_id = self.move_journal_id.id
                        move_id = self.env['account.move'].create({
                        'period_id': period_id,
                        'journal_id': move_journal_id,
                        'date': first_date_of_year,
                        'ref': "IB",
                        'is_incoming_balance_move':True,
                        #'journal_id': self.env['account.journal'].search([('type','=','general'),('company_id','=',self.env.ref('base.main_company').id)])[0].id,
                        })
                            
                        line_vals = {
                        'account_id': ib_account.id,
                        'credit': float(ib_amount) < 0 and float(ib_amount) * -1 or 0.0, #If ib_amount is negativ then we create a credit line in the account move otherwise a debit line
                        'debit': float(ib_amount) > 0 and float(ib_amount) or 0.0,
                        #'period_id': period_id,
                        'date': first_date_of_year,
                        #'quantity': trans_quantity,
                        'name': "#IB",
                        'move_id': move_id.id,
                        }

                        context_copy = self.env.context.copy()
                        context_copy.update({'check_move_validity':False})
                        trans_id = self.with_context(context_copy).env['account.move.line'].create(line_vals)

                        #Depending on the accounts used odoo will self balance the account moves by adding an opposite account, problem is that we don't know if that has happened or not.
                        #Checking if account move is balanced.
                        opposite_account = self.env['account.account'].search([('code','=','1930')])
                        move_balance = 0
                        for line in move_id.line_ids:
                          move_balance += line.balance
                        _logger.warning(f"{move_balance=}")
                        _logger.warning(f"{ib_amount=}")
                        _logger.warning(f"{float(move_balance) > 0 and float(move_balance) * -1 or 0.0}")
                        _logger.warning(f"{float(move_balance) > 0 and float(move_balance) * -1 or 0.0}")
                        if move_balance != 0:
                           line_vals = {
                           'account_id': opposite_account.id,
                           'credit': float(move_balance) > 0 and float(move_balance) or 0.0, #If ib_amount is negativ then we create a credit line in the account move otherwise a debit line
                           'debit': float(move_balance) < 0 and float(move_balance) * -1 or 0.0 or 0.0,
                           #'period_id': period_id,
                           'date': first_date_of_year,
                           #'quantity': trans_quantity,
                           'name': "#IB",
                           'move_id': move_id.id,
                           }
                           self.with_context(context_copy).env['account.move.line'].create(line_vals)
                           
                        
                    # ~ elif line['label'] == '#UB':
                        #Dont remember how i was supposed to create these, it wasn't account move at least i think?
                        #UB 0 1630 -1325.00
                        #UB årsnr konto saldo kvantitet
                        #context_copy = self.env.context.copy()
                        #context_copy.update({'check_move_validity':False})
                        #trans_id = self.with_context(context_copy).env['account.move.line'].create(line_vals)
                        #self.with_context(context_copy).env['account.move.line'].browse(trans_id.id)._compute_analytic_account_id()
        return ver_ids

