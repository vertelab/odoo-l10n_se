# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import RedirectWarning, UserError
from odoo import http
import base64
from datetime import datetime
from odoo.tools import date_utils
import odoo

import logging

_logger = logging.getLogger(__name__)


class account_sie_serie_to_journal(models.TransientModel):
    _name = 'account.sie.serie.to.journal'
    _description = 'SIE Serie to Journal'

    name = fields.Char(string="Serie")
    journal_id = fields.Many2one(comodel_name="account.journal", string="Journal",
                                 help="Used to set journal based on Serie of #VER", )
    sie_export = fields.Many2one(comodel_name="account.sie")

class account_sie_account(models.TransientModel):
    _name = 'account.sie.account'
    _description = 'SIE Import New Account Line'

    @api.model
    def default_user_type(self):
        return "asset_fixed"

    wizard_id = fields.Many2one(comodel_name='account.sie', string='Wizard')
    checked = fields.Boolean(string='')
    reconcile = fields.Boolean(string='')
    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', size=64, required=True)

    account_type = fields.Selection(
        selection=[
            ("asset_receivable", "Receivable"),
            ("asset_cash", "Bank and Cash"),
            ("asset_current", "Current Assets"),
            ("asset_non_current", "Non-current Assets"),
            ("asset_prepayments", "Prepayments"),
            ("asset_fixed", "Fixed Assets"),
            ("liability_payable", "Payable"),
            ("liability_credit_card", "Credit Card"),
            ("liability_current", "Current Liabilities"),
            ("liability_non_current", "Non-current Liabilities"),
            ("equity", "Equity"),
            ("equity_unaffected", "Current Year Earnings"),
            ("income", "Income"),
            ("income_other", "Other Income"),
            ("expense", "Expenses"),
            ("expense_depreciation", "Depreciation"),
            ("expense_direct_cost", "Cost of Revenue"),
            ("off_balance", "Off-Balance Sheet"),
        ],
        string="Type",
        required=True,
        default="asset_fixed",
    )

    parent_id = fields.Many2one(comodel_name='account.account', string='Parent', domain=[('type', '=', 'view')])

class account_sie(models.TransientModel):
    _name = 'account.sie'
    _description = 'SIE Import Wizard'
    sie_type = fields.Selection([('4i','Typ 4i Endast Verifikationsposter')],string='Sie Type', default='4i')


    def _set_company_domain(self):
        return [('company_id', '=', self.env.company.id)]

    serie_to_journal_ids = fields.One2many('account.sie.serie.to.journal', 'sie_export', string='Series to Journal')
    #date_start = fields.Date(string="Date interval")
    #date_stop = fields.Date(string="Stop Date")
    

    date_start = fields.Date(
        string="Date interval",
        default=lambda self: fields.Date.today()
    )
    date_stop = fields.Date(
        string="Stop Date",
        default=lambda self: fields.Date.today()
    )
                          
    journal_ids = fields.Many2many(comodel_name="account.journal", string="Journal",
                                   help="Moves with this type of journals")
    partner_ids = fields.Many2many(comodel_name="res.partner", string="Partner", help="Moves tied to these partners",
                                   domain=_set_company_domain)
    #account_ids = fields.Many2many(comodel_name="account.account", string="Account", domain=[('company_ids', 'in', [self.env.company.id)]])
    
    account_ids = fields.Many2many(
        comodel_name='account.account',
        string='Account',
        domain=lambda self: [('company_ids', 'in', [self.env.company.id])],
    )
    account_line_ids = fields.One2many(comodel_name='account.sie.account', inverse_name='wizard_id',
                                       string='New Accounts')
    state = fields.Selection([('choose', 'choose'), ('get', 'get'), ], default="choose")
    date_field_to_use = fields.Selection([('go_by_date', 'Go by Date'), ],
                                         string="Filter On Date", default="go_by_date")
    data = fields.Binary('File')
    filename = fields.Char(string='Filename')
    show_account_lines = fields.Boolean(string='Show Account Lines')
    move_journal_id = fields.Many2one(comodel_name="account.journal", string="Journal",
                                      help="All imported account.moves will get this journal",
                                      domain=_set_company_domain)
    company_id = fields.Many2one('res.company', related='move_journal_id.company_id')
    #company_id = fields.Many2one('res.company')
    accounts_type = fields.Selection(
        selection=[
            ("asset_receivable", "Receivable"),
            ("asset_cash", "Bank and Cash"),
            ("asset_current", "Current Assets"),
            ("asset_non_current", "Non-current Assets"),
            ("asset_prepayments", "Prepayments"),
            ("asset_fixed", "Fixed Assets"),
            ("liability_payable", "Payable"),
            ("liability_credit_card", "Credit Card"),
            ("liability_current", "Current Liabilities"),
            ("liability_non_current", "Non-current Liabilities"),
            ("equity", "Equity"),
            ("equity_unaffected", "Current Year Earnings"),
            ("income", "Income"),
            ("income_other", "Other Income"),
            ("expense", "Expenses"),
            ("expense_depreciation", "Depreciation"),
            ("expense_direct_cost", "Cost of Revenue"),
            ("off_balance", "Off-Balance Sheet"),
        ],
        string="Type",
        required=True,
        default="asset_fixed",
    )

    accounts_parent_id = fields.Many2one(comodel_name='account.account', string='Parent',
                                         domain=[('type', '=', 'view')])
  
        
    def _data(self):
        self.sie_file = self.data

    sie_file = fields.Binary(compute='_data')

    @api.model
    def cleanse_with_fire(self, data):
        data = base64.decodebytes(data or '').decode('cp437')
        text_list = []
        for line in data.split('\n'):
            line = line.strip()
            if line:
                text_list.append(line)
        data = self.read_file(text_list)
        return data

    def check_import_file(self, data=None, check_periods=True):
        self.ensure_one()
        if data or self.data:  # IMPORT TRIGGERED
            data = data or self.cleanse_with_fire(self.data)
            missing_accounts = self.env['account.account'].check__missing_accounts(self._import_accounts(data))
            if len(missing_accounts) > 0:
                return False
            return True
        else:
            return False

    def create_accounts(self):
        self.ensure_one()
        for line in self.account_line_ids:
            self.env['account.account'].create({
                'company_id': self.company_id.id,
                'name': line.name,
                'code': line.code,
                'account_type': line.account_type,
                # 'user_type_id': line.user_type.id,
                'root_id': line.parent_id and line.parent_id.id or None,
                'reconcile': line.reconcile,
            })
        self.account_line_ids = None
        self.show_account_lines = False

    @api.model
    def read_line(self, line, i=0):
        # TRANS 2013 {} 15887 "" "" 0
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
                        if field == '' and "#TRANS" in line:
                            # just an empty "", we still need that in order to deterimine which value was in which index.
                            field = "Empty Citation"
                        if field == '' and "#VER" in line:
                            # just an empty "", we still need that in order to deterimine which value was in which index.
                            field = " "
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
    def read_file(self, text_list, i=0):
        # ~ _logger.warning(f"{text_list}")
        res = []
        last_line = None
        while i < len(text_list):
            _logger.debug(i)
            _logger.warning(f"before {i=} {text_list[i]=}")
            if text_list[i] == '{':
                _logger.debug('down')
                l, i = self.read_file(text_list, i + 1)
                last_line['lines'] = l
            elif text_list[i] == '}':
                _logger.debug('up')
                return res, i
            else:
                _logger.warning(f"after {i=} {text_list[i]=}")

                l = self.read_line(text_list[i])
                _logger.warning(f"{l=}")
                last_line = {}
                for x in range(len(l)):
                    if x == 0:
                        last_line['label'] = l[x]
                    else:
                        last_line[x] = l[x]
                _logger.warning(f"{last_line=}")
                res.append(last_line)
            i += 1
        return res

    def get_missing_accounts(self):
        if self.data:
            data = self.cleanse_with_fire(self.data)

            if not self.check_import_file(data):
                missing_accounts = self.env['account.account'].check__missing_accounts(self._import_accounts(data))
                for account in missing_accounts:
                    sie_account_id = self.env['account.sie.account'].search([
                        ('code', '=', account[0]), ('wizard_id', '=', self.id)
                    ], limit=1)
                    if not sie_account_id:
                        self.write({
                            'account_line_ids': [
                                (0, 0, {
                                    'code': account[0], 'name': account[1],
                                    # 'user_type': account_type[0].id,
                                    # "reconcile": be_reconcilable
                                })
                            ]
                        })
                    else:
                        self.write({
                            'account_line_ids': [
                                (1, sie_account_id.id, {
                                    'code': account[0], 'name': account[1],
                                    # "reconcile": be_reconcilable
                                })
                            ]
                        })
                        
    def move_search_domain(self):
        search = []
        search.append(('state', '=', 'posted'))
        search.append(('company_id.id', '=', self.env.company.id))
        if self.date_start:
            search.append(('date', '>=', self.date_start))
            search.append(('date', '<=', self.date_stop))
        if self.journal_ids:
            search.append(('journal_id', 'in', [j.id for j in self.journal_ids]))
        if self.partner_ids:
            search.append(('partner_id', 'in', [p.id for p in self.partner_ids]))
        return search

    def send_form(self):
        self.ensure_one()

        if self.data:  # IMPORT TRIGGERED
            if not self.move_journal_id:
                raise UserError(f"Please select a journal")
            data = self.cleanse_with_fire(self.data)
            if not self.check_import_file(data):
                missing_accounts = self.env['account.account'].check__missing_accounts(self._import_accounts(data))
                formatstring = ""
                for account in missing_accounts:
                    formatstring += account[0] + ": " + account[1] + "\n"
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': "Missing Accounts",
                        'message': "Some accounts are missing",
                        'sticky': False,
                    }
                }
            ver_ids = self._import_ver(data)
            action = self.env['ir.actions.act_window']._for_xml_id('account.action_move_journal_line')
            action['res_ids'] = ver_ids
            return action
        else:
            if self.sie_type == "4i" or self.sie_type == "4e":
                search = self.move_search_domain()
                move_ids = self.env['account.move'].search(search)
                if self.account_ids:
                    accounts = [l.move_id.id for l in self.env['account.move.line'].search(
                        [('account_id', 'in', [a.id for a in self.account_ids])])]
                    move_ids = move_ids.filtered(lambda r: r.id in accounts)
                    
            self.write(
                {'state': 'get', 'data': base64.encodebytes(self.make_sie(move_ids)),
                 'filename': 'filename.se'})

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
        def get_accounts_ver(ver_ids):
            return ver_ids.mapped('line_ids.account_id')

        def get_accounts_sie_dict(sie_dict):
            dict_accounts = []
            if sie_dict:
                for line in sie_dict:
                    dict_accounts.append(line['account_code'])
                dict_accounts = set(dict_accounts)
                dict_accounts_records = self.env['account.account']
                for line in dict_accounts:
                    dict_accounts_records += self.env['account.account'].search([('code', '=', line)])
                return dict_accounts_records

        def get_accounts(ver_ids):
            #accounts = self.env['account.account']
            if ver_ids:
                return get_accounts_ver(ver_ids)
            #accounts = sorted(accounts, key=lambda r: r.code, reverse=True)
            return False

        if len(self) > 0:
            sie_form = self[0]
        company = self.env.company
        user = self.env['res.users'].browse(self._context['uid'])

        str = ''
        str += '#FLAGGA 0\n'
        str += '#PROGRAM "Odoo" %s\n' % odoo.service.common.exp_version()['server_serie']
        str += '#FORMAT PC8\n'  # ,Anger vilken teckenuppsattning som anvants
        str += '#GEN %s\n' % fields.Date.today().strftime("%Y%m%d")
        str += '#SIETYP 4\n'
        
              
        str += '#FNAMN "%s"\n' % company.name
        str += '#ORGNR %s\n' % company.company_registry
        str += '#ADRESS "%s" "%s" "%s %s" "%s"\n' % (
            user.display_name, company.street, company.zip, company.city, company.phone)
        str += '#KPTYP %s\n' % (company.kptyp if company.kptyp else 'BAS2015')

        for account in get_accounts(ver_ids):
            str += '#KONTO %s "%s"\n' % (account.code, account.name)
        ub = {}
        ub_accounts = []
        for ver in ver_ids:
            str += '#VER %s "%s" %s "%s" %s %s\n{\n' % (self.escape_sie_string(ver.journal_id.type), ver.id,
                                                        self.escape_sie_string(ver.date.strftime("%Y%m%d")),
                                                        self.escape_sie_string(self.fix_empty(ver.narration))[:20],
                                                        self.escape_sie_string(ver.create_date.strftime("%Y%m%d")),
                                                        self.escape_sie_string(ver.create_uid.login))
            for trans in ver.line_ids:
                if trans.display_type == "line_note" or trans.display_type == 'line_section':
                    continue
                str += '#TRANS %s {} %s %s "%s" %s %s\n' % (
                    self.escape_sie_string(trans.account_id.code), trans.debit - trans.credit,
                    self.escape_sie_string(trans.date.strftime("%Y%m%d")),
                    self.escape_sie_string(self.fix_empty(trans.name)), trans.quantity,
                    self.escape_sie_string(trans.create_uid.login))
                if trans.account_id.code not in ub:
                    ub[trans.account_id.code] = 0.0
                ub[trans.account_id.code] += trans.debit - trans.credit
            str += '}\n'

        return str.encode('cp437', 'xmlcharrefreplace')  # ignore

    @api.model
    def escape_sie_string(self, s):
        return s.replace('\n', ' ').replace('\\', '\\\\').replace('"', '\\"')
        
    @api.model
    def export_sie(self, ver_ids):
        if len(self) < 1:
            sie_form = self.create({})
        else:
            sie_form = self[0]
        _logger.info('export: %s' % ver_ids)
        result = sie_form.make_sie(ver_ids)
        filetest = base64.b64encode(result)
        sie_form.write(
            {'state': 'get', 'data': base64.b64encode(sie_form.make_sie(ver_ids)), 'filename': 'filename.se'})
        view = self.env.ref('l10n_se_sie_minimal.wizard_account_sie', False)
        _logger.info('view %s sie_form %s %s %s' % (
            view, sie_form, sie_form.sie_file, base64.b64encode(sie_form.make_sie(ver_ids))))
        # ~ sie_form.write({'state': 'get', 'data': base64.b64encode(self.make_sie()) })
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
        if (narration):
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
        raise UserError(sie_form.data)


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
            elif (not quote and s == len(string) - 1 and not string[s] == ' '):
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
                # During the process of reading the example file we sometimes don't have a value in index 2. This happens when a line in the example file looks like this ' #KONTO 3019 "" '
                if len(line) < 3:
                    accounts.append((line[1], ""))
                else:
                    accounts.append((line[1], line[2]))
            if line['label'] == "#RAR":
               _logger.warning(f"RAR {line}")
               if line[1] == '0':
                  date_start_string = line[2]
                  date_start_object = fields.Date.to_date(datetime.strptime(date_start_string, "%Y%m%d").date())
                  
                  date_end_string = line[3]
                  date_end_object = fields.Date.to_date(datetime.strptime(date_end_string, "%Y%m%d").date())

                  # Use the converted date in your search query
                  self.first_transaction_year_in_file = fiscal_year = self.env['account.fiscalyear'].search([
                    ('date_start', '=', date_start_object),
                    ('date_stop', '=', date_end_object),
                    ('company_id', '=', self.env.company.id)
                    ], limit=1)
                  if not self.first_transaction_year_in_file:
                     raise UserError(f"Saknar böföringsår för #RAR {line[1]} {line[2]}- {line[3]}")
                              
        return accounts

        
    def postfix_line_vals(self, line_vals):
        #Purpose is to inherit and if changes are need they can be made here.
        return line_vals

    def _import_ver(self, data):
        self.ensure_one()
        journal_types = []
        ver_ids = self.env['account.move']

        tag_table = {}
        for line in data:
            if line['label'] == '#VER':

                list_date = line.get(3)  # date
                list_ref = line.get(1, " ") + ' ' + line.get(2, " ") + ' ' + line.get(4, " ")  # reference
                list_sign = line.get(5)  # sign
                list_regdatum = line.get(5)  # created_date

                move_journal_id = self.move_journal_id.id

                serie_to_journal_lines = self.serie_to_journal_ids.filtered(lambda x: x.name == line.get(1))

                if len(serie_to_journal_lines) > 1:
                    serie_to_journal_lines_warning = "There are two lines the same series.\n"
                    for serie_to_journal_line in serie_to_journal_lines:
                        serie_to_journal_lines_warning += f"{serie_to_journal_line.name} = {serie_to_journal_line.journal_id.name} \n"
                    serie_to_journal_lines_warning += "Please remove one of the lines."
                    raise UserError(serie_to_journal_lines_warning)

                elif len(serie_to_journal_lines) == 1:
                    move_journal_id = serie_to_journal_lines.journal_id.id

                ver_id = self.env['account.move'].with_context({'check_move_period_validity': False}).create({
                    'journal_id': move_journal_id,
                    'date': list_date[0:4] + '-' + list_date[4:6] + '-' + list_date[6:],
                    'ref': list_ref,
                })
                ver_ids += ver_id

                for l in line.get('lines', []):

                    if l['label'] == '#TRANS':
                        # https://sie.se/wp-content/uploads/2020/05/SIE_filformat_ver_4B_080930.pdf
                        # Documentation om hur en ver post ska se ut, den har ett antal frivilliga poster så det är jätte strörrande
                        # Format:#TRANS kontonr {objektlista} belopp transdat(Frivilig) transtext(Frivilig) kvantitet(Frivilig) sign(Frivilig)

                        trans_code = l[1]
                        trans_object = [(l[2][i * 2], l[2][i * 2 + 1]) for i in range(int(len(l[2]) / 2))]
                        trans_balance = l[3]
                        trans_name = '#'
                        trans_date = l.get(4)
                        trans_name = l.get(5)
                        trans_quantity = l.get(6)
                        trans_sign = l.get(7)
                        code = self.env['account.account'].search(
                            [('code', '=', trans_code), ("company_id", '=', self.company_id.id)],
                            limit=1)


                        if trans_date and trans_date != "Empty Citation":
                            formated_date = trans_date[0:4] + '-' + trans_date[4:6] + '-' + trans_date[6:]
                        else:
                            formated_date = ver_id.date

                        if trans_name and trans_name == "Empty Citation":
                            trans_name = ""

                        line_vals = {
                                'account_id': code.id,
                                'credit': float(trans_balance) < 0 and float(trans_balance) * -1 or 0.0,
                                'debit': float(trans_balance) > 0 and float(trans_balance) or 0.0,
                                'date': formated_date,
                                'name': trans_name,
                                'move_id': ver_id.id,
                                'currency_id': code.currency_id.id if code.currency_id else self.company_id.currency_id.id
                        }

                        line_vals = self.postfix_line_vals(line_vals)
                        
                        context_copy = self.env.context.copy()
                        context_copy.update({'check_move_validity': False, 'check_move_period_validity': False})
                        trans_id = self.with_context(context_copy).env['account.move.line'].create(line_vals)
                        tax_line_id = self.env['account.tax'].search([('name', '=ilike', trans_name)]).id
                        if tax_line_id:
                            trans_id.tax_line_id = tax_line_id

        return ver_ids
