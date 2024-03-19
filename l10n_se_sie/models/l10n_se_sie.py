# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import Warning, RedirectWarning, UserError
from odoo import http
import base64
from datetime import datetime
import odoo

import logging

_logger = logging.getLogger(__name__)


class account_sie_serie_to_journal(models.TransientModel):
    _name = 'account.sie.serie.to.journal'

    name = fields.Char(string="Serie")
    journal_id = fields.Many2one(comodel_name="account.journal", string="Journal",
                                 help="Used to set journal based on Serie of #VER", )
    sie_export = fields.Many2one(comodel_name="account.sie")


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
        ('liquidity', 'Liquidity'),
        ('consolidation', 'Consolidation'),
        ('closed', 'Closed'),
    ], string='Internal Type', default='other', required=True,
        help="The 'Internal Type' is used for features available on " \
             "different types of accounts: view can not have journal items, consolidation are accounts that " \
             "can have children accounts for multi-company consolidations, payable/receivable are for " \
             "partners accounts (for debit/credit computations), closed for depreciated accounts.")
    user_type = fields.Many2one('account.account.type', 'Account Type', required=True, default=default_user_type,
                                help="Account Type is used for information purpose, to generate "
                                     "country-specific legal reports, and set the rules to close a fiscal year and generate opening entries.")
    parent_id = fields.Many2one(comodel_name='account.account', string='Parent', domain=[('type', '=', 'view')])


class account_sie(models.TransientModel):
    _name = 'account.sie'
    _description = 'SIE Import Wizard'

    ####
    include_transactions = fields.Boolean('Include Transactions')
    include_ib = fields.Boolean("Include Incoming Balans")

    # ~ include_ub = fields.Boolean("Include Outgoing Balans")
    # ~ include_res = fields.Boolean("Include Res Balans")

    def _get_default_current_fiscalyear(self):
        return self.env['account.fiscalyear'].search(
            [('date_start', '<=', fields.Date.today()), ('date_stop', '>=', fields.Date.today()),
             ('company_id', '=', self.env.company.id)], limit=1)

    def _set_period_fiscal_domain(self):
        return [('company_id', '=', self.env.company.id)]

    current_transaction_year = fields.Many2one(comodel_name="account.fiscalyear", string="Current Fiscal Year",
                                               help="Balanse posts are relativ to this fiscal year",
                                               domain=_set_period_fiscal_domain,
                                               default=_get_default_current_fiscalyear)
    ib_fiscalyear_ids = fields.Many2many(comodel_name="account.fiscalyear",
                                         string="Incoming balans for these fiscal years",
                                         help="IB For Following fiscal years", domain=_set_period_fiscal_domain)
    #### 

    serie_to_journal_ids = fields.One2many('account.sie.serie.to.journal', 'sie_export', string='Series to Journal')
    date_start = fields.Date(string="Date interval")
    date_stop = fields.Date(string="Stop Date")
    period_ids = fields.Many2many(comodel_name="account.period",
                                  string="Periods", domain=_set_period_fiscal_domain)

    fiscalyear_ids = fields.Many2one(comodel_name="account.fiscalyear", string="Fiscal Year",
                                     help="Moves in this fiscal years", domain=_set_period_fiscal_domain)
    journal_ids = fields.Many2many(comodel_name="account.journal", string="Journal",
                                   help="Moves with this type of journals")
    partner_ids = fields.Many2many(comodel_name="res.partner", string="Partner", help="Moves tied to these partners",
                                   domain=_set_period_fiscal_domain)
    account_ids = fields.Many2many(comodel_name="account.account", string="Account", domain=_set_period_fiscal_domain)
    account_line_ids = fields.One2many(comodel_name='account.sie.account', inverse_name='wizard_id',
                                       string='New Accounts')
    state = fields.Selection([('choose', 'choose'), ('get', 'get'), ], default="choose")
    date_field_to_use = fields.Selection(selection=[('go_by_period', 'Go by Period'), ('go_by_date', 'Go by Date'), ],
                                         string="Filter On Period or Date", default="go_by_period")
    data = fields.Binary('File')
    filename = fields.Char(string='Filename')
    show_account_lines = fields.Boolean(string='Show Account Lines')
    move_journal_id = fields.Many2one(comodel_name="account.journal", string="Journal",
                                      help="All imported account.moves will get this journal",
                                      domain=_set_period_fiscal_domain)
    company_id = fields.Many2one(related='move_journal_id.company_id')

    accounts_type = fields.Selection(selection=[
        ('view', 'View'),
        ('other', 'Regular'),
        ('receivable', 'Receivable'),
        ('payable', 'Payable'),
        ('liquidity', 'Liquidity'),
        ('consolidation', 'Consolidation'),
        ('closed', 'Closed'),
    ], string='Internal Type', help="The 'Internal Type' is used for features available on " \
                                    "different types of accounts: view can not have journal items, consolidation are accounts that " \
                                    "can have children accounts for multi-company consolidations, payable/receivable are for " \
                                    "partners accounts (for debit/credit computations), closed for depreciated accounts.")
    accounts_user_type = fields.Many2one('account.account.type', 'Account Type',
                                         help="Account Type is used for information purpose, to generate "
                                              "country-specific legal reports, and set the rules to close a fiscal year and generate opening entries.")
    accounts_parent_id = fields.Many2one(comodel_name='account.account', string='Parent',
                                         domain=[('type', '=', 'view')])

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
            # ~ _logger.warning(f"before {line=}")
            line = line.strip()
            # ~ _logger.warning(f"after {line=}")
            if line:
                text_list.append(line)
        # ~ _logger.warning(f"{text_list=}")
        data = self.read_file(text_list)
        # ~ _logger.warning(data)
        return data

    def check_import_file(self, data=None, check_periods=True):
        self.ensure_one()
        if data or self.data:  # IMPORT TRIGGERED
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
                'company_id': self.company_id.id,
                'name': line.name,
                'code': line.code,
                'internal_type': line.type,
                'user_type_id': line.user_type.id,
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
            # ~ _logger.warning(f"before {i=} {text_list[i]=}")
            if text_list[i] == '{':
                # ~ _logger.debug('down')
                l, i = self.read_file(text_list, i + 1)
                last_line['lines'] = l
            elif text_list[i] == '}':
                # ~ _logger.debug('up')
                return res, i
            else:
                # ~ _logger.warning(f"after {i=} {text_list[i]=}")

                l = self.read_line(text_list[i])
                # ~ _logger.warning(f"{l=}")
                last_line = {}
                for x in range(len(l)):
                    if x == 0:
                        last_line['label'] = l[x]
                    else:
                        last_line[x] = l[x]
                # ~ _logger.warning(f"{last_line=}")
                res.append(last_line)
            i += 1
        return res

    def get_missing_accounts(self):
        if self.data:
            data = self.cleanse_with_fire(self.data)

            if not self.check_import_file(data):
                missing_accounts = self.env['account.account'].check__missing_accounts(self._import_accounts(data))
                for account in missing_accounts:
                    # account type lookup
                    account_type = self.env['account.account.type']._account_type_lookup(code=account[0])
                    if not account_type:
                        account_type = self.env.ref('account.data_account_type_fixed_assets')

                    be_reconcilable = False
                    if account_type.type == "receivable" or account_type.type == "payable":
                        be_reconcilable = True

                    # check if account line exist
                    sie_account_id = self.env['account.sie.account'].search(
                        [('code', '=', account[0]), ('wizard_id', '=', self.id)
                         ], limit=1)
                    if not sie_account_id:
                        self.write({
                            'account_line_ids': [
                                (0, 0, {'code': account[0], 'name': account[1], 'user_type': account_type[0].id,
                                        "reconcile": be_reconcilable})
                            ]
                        })
                    else:
                        self.write({
                            'account_line_ids': [
                                (1, sie_account_id.id,
                                 {'code': account[0], 'name': account[1], "reconcile": be_reconcilable})
                            ]
                        })

    def send_form(self):
        self.ensure_one()

        if self.data:  # IMPORT TRIGGERED
            if not self.move_journal_id:
                raise Warning(f"Please select a journal")
            data = self.cleanse_with_fire(self.data)
            if not self.check_import_file(data):
                missing_accounts = self.env['account.account'].check__missing_accounts(self._import_accounts(data))
                formatstring = ""
                for account in missing_accounts:
                    formatstring += account[0] + ": " + account[1] + "\n"
                    # self._create_missing_accounts(account[0], account[1])

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
            move_ids = []
            ib_dict = {}
            if self.include_transactions:
                search = []
                search.append(('state', '=', 'posted'))
                search.append(('company_id.id', '=', self.env.company.id))
                if self.date_start:
                    search.append(('date', '>=', self.date_start))
                    search.append(('date', '<=', self.date_stop))
                if self.fiscalyear_ids:
                    search.append(('period_id', 'in', [p.id for p in self.fiscalyear_ids.period_ids]))
                if self.period_ids:
                    search.append(('period_id', 'in', [p.id for p in self.period_ids]))
                if self.journal_ids:
                    search.append(('journal_id', 'in', [j.id for j in self.journal_ids]))
                if self.partner_ids:
                    search.append(('partner_id', 'in', [p.id for p in self.partner_ids]))
                move_ids = self.env['account.move'].search(search)
                if self.account_ids:
                    accounts = [l.move_id.id for l in self.env['account.move.line'].search(
                        [('account_id', 'in', [a.id for a in self.account_ids])])]
                    move_ids = move_ids.filtered(lambda r: r.id in accounts)
            if self.include_ib:
                ib_dict = self.get_ib_value_dict()
            self.write(
                {'state': 'get', 'data': base64.encodestring(self.make_sie(move_ids, ib_dict)),
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

    def get_ib_value_dict(self):
        self.ensure_one()
        all_fiscal_years = self.env['account.fiscalyear'].search([('company_id', '=', self.env.company.id)],
                                                                 order='date_start ASC')
        current_fiscalyear_index = next(
            (index for index, fy in enumerate(all_fiscal_years) if fy.id == self.current_transaction_year.id), 0)
        formated_result = []

        for fiscalyear in self.ib_fiscalyear_ids:
            fiscalyear_index = next((index for index, fy in enumerate(all_fiscal_years) if fy.id == fiscalyear.id), 0)

            year_nr = fiscalyear_index - current_fiscalyear_index
            previous_years = all_fiscal_years[0:fiscalyear_index]
            _logger.warning(f"{fiscalyear_index=}")
            _logger.warning(f"{all_fiscal_years=}")
            _logger.warning(f"{previous_years=}")
            ib_search = []
            ib_search.append(('move_id.state', '=', 'posted'))
            ib_search.append(('move_id.company_id', '=', self.env.company.id))
            if self.date_field_to_use == "go_by_period":
                ib_search.append(('move_id.period_id', 'in', [p.id for p in previous_years.period_ids]))
            else:
                ib_search.append(('move_id.date', '>=', previous_years[0].date_start))
                ib_search.append(('move_id.date', '<=', previous_years[-1].date_stop))
            ib_search.append(('account_id.user_type_id.report_type', '=', "b"))

            result = self.env['account.move.line'].search(ib_search)

            result = self.env['account.move.line'].read_group(
                ib_search,
                ['account_id', 'debit', 'credit'],
                ['account_id']
            )
            _logger.warning(f"{result=}")
            for res in result:
                better_dict = {}
                better_dict['yearnr'] = year_nr
                better_dict['account_code'] = self.env['account.account'].browse(res['account_id'][0]).code
                better_dict['balance'] = res['debit'] - res['credit']
                formated_result.append(better_dict)
            # _logger.warning(f"{better_dict=}")
        return formated_result

    def make_sie(self, ver_ids, ib_dict):
        def get_fiscalyears(ver_ids):
            year_list = set()
            for ver in ver_ids:
                year_list.add(ver.period_id.fiscalyear_id)
            return year_list

        def get_accounts_ver(ver_ids):
            return ver_ids.mapped('line_ids.account_id')

        def get_accounts_ib(ib_dict):
            ib_dict_accounts = []
            if ib_dict:
                for line in ib_dict:
                    ib_dict_accounts.append(line['account_code'])
                ib_dict_accounts = set(ib_dict_accounts)
                ib_dict_accounts_records = self.env['account.account']
                for line in ib_dict_accounts:
                    ib_dict_accounts_records += self.env['account.account'].search([('code', '=', line)])
                return ib_dict_accounts_records

        def get_accounts(ver_ids, ib_dict):
            if ver_ids and ib_dict:
                return list(set(get_accounts_ver(ver_ids) | get_accounts_ib(ib_dict)))
            if ver_ids:
                return list(set(get_accounts_ver(ver_ids)))
            if ib_dict:
                return list(set(get_accounts_ib(ib_dict)))
            return []

        if len(self) > 0:
            sie_form = self[0]
        company = self.env.company
        if ver_ids:
            fiscalyear = ver_ids[0].period_id.fiscalyear_id
        else:
            self.current_transaction_year
        user = self.env['res.users'].browse(self._context['uid'])

        str = ''
        str += '#FLAGGA 0\n'
        str += '#PROGRAM "Odoo" %s\n' % odoo.service.common.exp_version()['server_serie']
        str += '#FORMAT PC8\n'  # ,Anger vilken teckenuppsattning som anvants
        str += '#GEN %s\n' % fields.Date.today().strftime("%Y%m%d")
        str += '#SIETYP 4\n'
        for fiscalyear in get_fiscalyears(ver_ids):
            str += '#RAR %s %s %s\n' % (self._get_rar_code(fiscalyear), fiscalyear.date_start.strftime("%Y%m%d"),
                                        fiscalyear.date_stop.strftime("%Y%m%d"))
        str += '#FNAMN "%s"\n' % company.name
        str += '#ORGNR %s\n' % company.company_registry
        str += '#ADRESS "%s" "%s" "%s %s" "%s"\n' % (
            user.display_name, company.street, company.zip, company.city, company.phone)
        str += '#KPTYP %s\n' % (company.kptyp if company.kptyp else 'BAS2015')

        for account in get_accounts(ver_ids, ib_dict):
            str += '#KONTO %s "%s"\n' % (account.code, account.name)
        ub = {}
        ub_accounts = []
        for ver in ver_ids:
            # ~ _logger.warning(f"{ver=}")
            if ver.period_id.special == False:
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

        for ib_val in ib_dict:  # {'yearnr': -1, 'account_code': '1079', 'balance': 5000.0}, # IB
            str += '#IB %s %s %s\n' % (
                ib_val['yearnr'], ib_val['account_code'],
                ib_val['balance'])
            _logger.warning('#IB %s %s %s\n' % (
                ib_val['yearnr'], ib_val['account_code'],
                ib_val['balance']))
        # TODO #RES OCH #UB Borde vara för nyvarande

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
        view = self.env.ref('l10n_se_sie.wizard_account_sie', False)
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
        raise Warning(sie_form.data)
        # ~ result = {}
        # ~ for product_data in self.browse(cr, uid, ids, context=context):
        # ~ result[product_data.id] = product_data['file_path']
        # ~ return result
        # ~ return result

        # _logger.warning('\n%s' % base64.encodestring(args.get('data').read()))

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
        return accounts

    def _check_periods(self, data):
        missing_period = []
        for line in data:
            if line['label'] == '#VER':
                try:
                    # ~ _logger.warning(f"WHAT: {self.env['account.period'].search([], limit=1)}")
                    # self.env['account.period'].find(dt=line[3]) #Expected singleton
                    self.env['account.period'].search([], limit=1).find(
                        dt=line[3],
                        company_id=self.company_id.id)  # The find method has self.ensure_one, which is why i find one record.
                except RedirectWarning:
                    _logger.warning(f"{line[3]=}")
                    if not missing_period:
                        missing_period = [line[3], line[3]]
                    elif line[3] < missing_period[0]:
                        missing_period[0] = line[3]
                    elif line[3] > missing_period[1]:
                        missing_period[1] = line[3]
        _logger.warning(f"{missing_period=}")
        return missing_period

    def _import_ver(self, data):
        self.ensure_one()
        journal_types = []
        ver_ids = self.env['account.move']

        tag_table = {}
        ib_line_vals = []
        ib_move_id = False
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

                ver_id = self.env['account.move'].create({
                    'period_id': self.env['account.period'].search([], limit=1).find(dt=list_date,
                                                                                     company_id=self.company_id.id).id,
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
                        if code.user_type_id.report_type == 'income':
                            journal_types.append('sale' and float(trans_balance) > 0.0 or 'sale_refund')
                        elif code.user_type_id.id == self.env.ref(
                                'account.data_account_type_liquidity').id:  # changed from data_account_type_bank to data_account_type_liquidity
                            journal_types.append('bank')
                        elif code.user_type_id.id == self.env.ref(
                                'account.data_account_type_liquidity').id:  # changed from data_account_type_bank to data_account_type_liquidity
                            journal_types.append('cash')
                        elif code.user_type_id.report_type in ['asset', 'expense']:
                            journal_types.append('purchase' and float(trans_balance) > 0.0 or 'purchase_refund')

                        period_id = self.env['account.period'].search(
                            [], limit=1
                        ).find(dt=list_date, company_id=self.company_id.id).id
                        _logger.debug(
                            '\n account_id :%s\n balance: %s\n period_id: %s' % (code, trans_balance, period_id)
                        )

                        if trans_date and trans_date != "Empty Citation":
                            formated_date = trans_date[0:4] + '-' + trans_date[4:6] + '-' + trans_date[6:]
                        else:
                            formated_date = ver_id.date

                        if trans_name and trans_name == "Empty Citation":
                            trans_name = ""

                        tags = []
                        tag_model = self.env['account.analytic.tag']
                        for tag_type, tag_val in trans_object:
                            tag_name_prefix = f"{tag_val} %"  # Equivalent to 'regex': "^{tag_val} .*$"
                            if tag_name_prefix not in tag_table:
                                matching_tag = tag_model.search([('name', '=like', tag_name_prefix)])
                                if len(matching_tag) == 0:
                                    raise Warning(
                                        f"Missing tag for {'project' if tag_type == '6' else 'cost center'} {tag_val}")
                                if len(matching_tag) > 1:
                                    raise Warning(
                                        f"Too many tags matching {'project' if tag_type == '6' else 'cost center'} {tag_val}")
                                tag_table[tag_name_prefix] = matching_tag.id

                            tags.append((4, tag_table[tag_name_prefix], 0))

                        line_vals = {
                            'account_id': code.id,
                            'credit': float(trans_balance) < 0 and float(trans_balance) * -1 or 0.0,
                            'debit': float(trans_balance) > 0 and float(trans_balance) or 0.0,
                            'analytic_tag_ids': tags,
                            'date': formated_date,
                            'name': trans_name,
                            'move_id': ver_id.id,
                            'currency_id': code.currency_id.id if code.currency_id else self.company_id.currency_id.id
                        }

                        context_copy = self.env.context.copy()
                        context_copy.update({'check_move_validity': False})
                        trans_id = self.with_context(context_copy).env['account.move.line'].create(line_vals)
                        self.with_context(context_copy).env['account.move.line'].browse(
                            trans_id.id)._compute_analytic_account_id()
                        tax_line_id = self.env['account.tax'].search([('name', '=ilike', trans_name)]).id
                        if tax_line_id:
                            trans_id.tax_line_id = tax_line_id

            elif line['label'] == '#IB':
                year_num = int(line.get(1))  # Opening period for current fiscal year
                first_date_of_year = '%s-01-01' % (datetime.today().year + year_num)
                period_id = self.env['account.period'].search(
                    [('date_start', '=', first_date_of_year), ('date_stop', '=', first_date_of_year),
                     ("company_id", '=', self.company_id.id),
                     ('special', '=', True)]).id
                ib_account = self.env['account.account'].search(
                    [('code', '=', line.get(2)), ("company_id", '=', self.company_id.id)])
                ib_amount = line.get(3)
                ib_qnt = line.get(4)  # We already have a amount, what is the purpose of having a quantity as well

                ib_move_journal_id = self.move_journal_id.id
                if not ib_move_id:
                    ib_move_id = self.env['account.move'].create({
                        'period_id': period_id,
                        'journal_id': ib_move_journal_id,
                        'date': first_date_of_year,
                        'ref': "IB",
                        'is_incoming_balance_move': True,
                    })

                line_vals = {
                    'account_id': ib_account.id,
                    'credit': float(ib_amount) < 0 and float(ib_amount) * -1 or 0.0,
                    # If ib_amount is negativ then we create a credit line in the account move otherwise a debit line
                    'debit': float(ib_amount) > 0 and float(ib_amount) or 0.0,
                    'date': first_date_of_year,
                    'name': "#IB",
                    'move_id': ib_move_id.id,
                    'currency_id': ib_account.currency_id.id if ib_account.currency_id else self.company_id.currency_id.id
                }
                # ~ _logger.warning(f"{line_vals=}")
                context_copy = self.env.context.copy()
                context_copy.update({'check_move_validity': False})
                trans_id = self.with_context(context_copy).env['account.move.line'].create(line_vals)

        # Depending on the accounts used odoo will self balance the account moves by adding an opposite account,
        # problem is that we don't know if that has happened or not.
        # Checking if account move is balanced.
        opposite_account = self.env['account.account'].search(
            [("company_id", '=', self.company_id.id), ('code', '=', '1930')])
        move_balance = 0
        if ib_move_id:
            for line in ib_move_id.line_ids:
                move_balance += line.balance
            if move_balance != 0:
                line_vals = {
                    'account_id': opposite_account.id,
                    'credit': float(move_balance) > 0 and float(move_balance) or 0.0,
                    # If ib_amount is negativ then we create a credit line in the account move otherwise a debit line
                    'debit': float(move_balance) < 0 and float(move_balance) * -1 or 0.0 or 0.0,
                    'date': first_date_of_year,
                    'name': "#IB",
                    'move_id': ib_move_id.id,
                }
                self.with_context(context_copy).env['account.move.line'].create(line_vals)

        return ver_ids
