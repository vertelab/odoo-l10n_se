# -*- coding: utf-8 -*-
##############################################################################
#
#    odoo, Open Source Management Solution, third party addon
#    Copyright (C) 2004-2015 Vertel AB (<http://vertel.se>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo.exceptions import AccessError
from odoo import api, fields, models, _
from odoo import SUPERUSER_ID
from odoo.tools.safe_eval import safe_eval as eval

import logging
_logger = logging.getLogger(__name__)

# TODO: Move this wizard to a general module.


class WizardModelUsage(models.TransientModel):
    """
    Find out where a model is used.
    """

    _name = 'wizard.object.usage'
    _description = 'Find Object Usage'
    
    model_id = fields.Many2one('ir.model', string='Model')
    results = fields.Html('Results')
    filter = fields.Char('Object IDs', default='[]')
    
    @api.onchange('model_id')
    def find_model_usage(self):
        results = ''
        filter_ids = eval(self.filter)
        if self.model_id:
            object_ids = set()
            props = self.env['ir.property'].search([('value_reference', '=like', '%s,%%' % self.model_id.model)])
            properties = '<table class="table table-striped">' \
                         '  <thead>' \
                         '    <tr>' \
                         '      <th>Model</th>' \
                         '      <th>Name</th>' \
                         '      <th>Value</th>' \
                         '    </tr>' \
                         '  </thead>' \
                         '  <tbody>\n'
            for prop in props:
                id = int(prop.value_reference.split(',')[1])
                if filter_ids and id not in filter_ids:
                    continue
                object_ids.add(id)
                properties += '    <tr>' \
                              '      <td>%s</td>' \
                              '      <td>%s</td>' \
                              '      <td>%s</td>' \
                              '    <tr>\n' % (prop.fields_id.model_id.name, prop.name, id)
            properties += '  </tbody>' \
                          '</table>'
            query = """select concat(R.TABLE_NAME, '.',  R.COLUMN_NAME)
from INFORMATION_SCHEMA.CONSTRAINT_COLUMN_USAGE u            
inner join INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS FK
    on U.CONSTRAINT_CATALOG = FK.UNIQUE_CONSTRAINT_CATALOG
    and U.CONSTRAINT_SCHEMA = FK.UNIQUE_CONSTRAINT_SCHEMA
    and U.CONSTRAINT_NAME = FK.UNIQUE_CONSTRAINT_NAME
inner join INFORMATION_SCHEMA.KEY_COLUMN_USAGE R
    ON R.CONSTRAINT_CATALOG = FK.CONSTRAINT_CATALOG
    AND R.CONSTRAINT_SCHEMA = FK.CONSTRAINT_SCHEMA
    AND R.CONSTRAINT_NAME = FK.CONSTRAINT_NAME
WHERE U.COLUMN_NAME = 'id'
  AND U.TABLE_NAME = '%s';""" % self.env[self.model_id.model]._table
            self.env.cr.execute(query)
            tables = {}
            for row in self.env.cr.fetchall():
                table, column = row[0].split('.')
                if table not in tables:
                    tables[table] = []
                tables[table].append(column)
            _logger.warning(tables)
            for table in tables:
                self.env.cr.execute("SELECT a.attname FROM pg_index i JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey) WHERE i.indrelid = '%s'::regclass AND i.indisprimary" % table)
                primary_key = self.env.cr.fetchall()
                primary_key = primary_key and primary_key[0][0]
                res = []
                for column in tables[table]:
                    if filter_ids:
                        where = "%s IN %%s" % column
                    else:
                        where = "%s IS NOT NULL" % column
                    if primary_key:
                        query = "SELECT %s AS primary_key, %s FROM %s WHERE %s" % (primary_key, column, table, where)
                    else:
                        query = "SELECT %s FROM %s WHERE %s" % (column, table, where)
                    self.env.cr.execute(query, filter_ids and [tuple(filter_ids)] or [])
                    res += self.env.cr.dictfetchall()
                if res:
                    results += '<table class="table table-striped">' \
                               '  <thead>' \
                               '    <tr>' \
                               '      <th>Table</th>' \
                               '      <th>Column</th>' \
                               '      <th>Value</th>' \
                               '      <th>%s</th>' \
                               '    </tr>' \
                               '  </thead>' \
                               '  <tbody>\n' % (primary_key or '')
                    for d in res:
                        for key in d:
                            if key != 'primary_key':
                                column = key
                        object_ids.add(d[column])
                        results += '    <tr>' \
                                   '      <td>%s</td>' \
                                   '      <td>%s</td>' \
                                   '      <td>%s</td>' \
                                   '      <td>%s</td>' \
                                   '    <tr>\n' % (table, column, d[column], d.get('primary_key', ''))
                    results += '  </tbody>' \
                               '</table>' \
                               '<br/>\n'
            self.results = '<h1>Total</h1>' \
                           '<p>Found %s references to %s</p>' \
                           '<p>%s</p>' \
                           '<h1>Properties</h1>' \
                           '%s' \
                           '<h1>Relations</h1>' \
                           '%s' % (
                                len(object_ids),
                                self.model_id.name,
                                ', '.join([str(i) for i in object_ids]),
                                properties,
                                results) 
            #~ query = []
            #~ for table in tables:
                #~ for col in res[table]:
                    #~ query.append("SELECT %s AS id FROM %s WHERE %s IS NOT NULL" % (col, table, col))
            #~ query = ' UNION '.join(query)
            #~ object_ids = [r[0] for r in self.env.cr.execute(query)]
            

# class AccountBankAccountsWizard(models.TransientModel):
#     _name = 'account.bank.accounts.wizard2'
#     _inherit = 'account.bank.accounts.wizard'
#
#     bank_account_id = fields.Many2one('wizard.change.charts.accounts', string='Bank Account', required=True,
#                                       ondelete='cascade')


class WizardChangeChartsAccounts(models.TransientModel):
    """
    Change account chart for a company.
    Wizards ask for:
        * a company
        * an account chart template
        * a number of digits for formatting code of non-view accounts
        * a list of bank accounts owned by the company
    Then, the wizard:
        * generates all accounts from the template and assigns them to the right company
        * generates all taxes and tax codes, changing account assignations
        * generates all accounting properties and assigns them correctly
    """

    _name = 'wizard.change.charts.accounts'
    _inherit = 'res.config'

    company_id = fields.Many2one('res.company', string='Company', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', help="Currency as per company's country.",
                                  required=True)
    only_one_chart_template = fields.Boolean(string='Only One Chart Template Available')
    chart_template_id = fields.Many2one('account.chart.template', string='Chart Template', required=True)
    
    bank_account_ids = fields.Char(string='Cash and Banks', required=True)
    
    bank_account_code_prefix = fields.Char('Bank Accounts Prefix', oldname="bank_account_code_char")
    cash_account_code_prefix = fields.Char('Cash Accounts Prefix')
    code_digits = fields.Integer(string='# of Digits', required=True, help="No. of Digits to use for account code")
    sale_tax_id = fields.Many2one('account.tax.template', string='Default Sales Tax', oldname="sale_tax")
    purchase_tax_id = fields.Many2one('account.tax.template', string='Default Purchase Tax', oldname="purchase_tax")
    sale_tax_rate = fields.Float(string='Sales Tax(%)')
    use_anglo_saxon = fields.Boolean(string='Use Anglo-Saxon Accounting', related='chart_template_id.use_anglo_saxon')
    transfer_account_id = fields.Many2one('account.account.template', required=True, string='Transfer Account',
                                          domain=lambda self: [('reconcile', '=', True),
                                                               ('user_type_id.id', '=', self.env.ref('account.data_account_type_current_assets').id)],
        help="Intermediary account used when moving money from a liquidity account to another")
    purchase_tax_rate = fields.Float(string='Purchase Tax(%)')
    complete_tax_set = fields.Boolean('Complete Set of Taxes',
        help="This boolean helps you to choose if you want to propose to the user to encode the sales and purchase rates or use "
            "the usual m2o fields. This last choice assumes that the set of tax defined for the chosen template is complete")

    @api.model
    def _get_chart_parent_ids(self, chart_template):
        """ Returns the IDs of all ancestor charts, including the chart itself.
            (inverse of child_of operator)

            :param browse_record chart_template: the account.chart.template record
            :return: the IDS of all ancestor charts, including the chart itself.
        """
        result = [chart_template.id]
        while chart_template.parent_id:
            chart_template = chart_template.parent_id
            result.append(chart_template.id)
        return result

    @api.onchange('sale_tax_rate')
    def onchange_tax_rate(self):
        self.purchase_tax_rate = self.sale_tax_rate or False

    @api.onchange('chart_template_id')
    def onchange_chart_template_id(self):
        res = {}
        tax_templ_obj = self.env['account.tax.template']
        if self.chart_template_id:
            currency_id = self.chart_template_id.currency_id and self.chart_template_id.currency_id.id or self.env.user.company_id.currency_id.id
            self.complete_tax_set = self.chart_template_id.complete_tax_set
            self.currency_id = currency_id
            if self.chart_template_id.complete_tax_set:
            # default tax is given by the lowest sequence. For same sequence we will take the latest created as it will be the case for tax created while isntalling the generic chart of account
                chart_ids = self._get_chart_parent_ids(self.chart_template_id)
                base_tax_domain = [('chart_template_id', 'parent_of', chart_ids)]
                sale_tax_domain = base_tax_domain + [('type_tax_use', '=', 'sale')]
                purchase_tax_domain = base_tax_domain + [('type_tax_use', '=', 'purchase')]
                sale_tax = tax_templ_obj.search(sale_tax_domain, order="sequence, id desc", limit=1)
                purchase_tax = tax_templ_obj.search(purchase_tax_domain, order="sequence, id desc", limit=1)
                self.sale_tax_id = sale_tax.id
                self.purchase_tax_id = purchase_tax.id
                res.setdefault('domain', {})
                res['domain']['sale_tax_id'] = repr(sale_tax_domain)
                res['domain']['purchase_tax_id'] = repr(purchase_tax_domain)
            if self.chart_template_id.transfer_account_id:
                self.transfer_account_id = self.chart_template_id.transfer_account_id.id
            if self.chart_template_id.code_digits:
                self.code_digits = self.chart_template_id.code_digits
            if self.chart_template_id.bank_account_code_prefix:
                self.bank_account_code_prefix = self.chart_template_id.bank_account_code_prefix
            if self.chart_template_id.cash_account_code_prefix:
                self.cash_account_code_prefix = self.chart_template_id.cash_account_code_prefix
        return res

    @api.model
    def _get_default_bank_account_ids(self):
        return [{'acc_name': _('Cash'), 'account_type': 'cash'}, {'acc_name': _('Bank'), 'account_type': 'bank'}]

    @api.model
    def default_get(self, fields):
        context = self._context or {}
        res = super(WizardChangeChartsAccounts, self).default_get(fields)
        tax_templ_obj = self.env['account.tax.template']
        account_chart_template = self.env['account.chart.template']

        if 'bank_account_ids' in fields:
            res.update({'bank_account_ids': self._get_default_bank_account_ids()})
        if 'company_id' in fields:
            res.update({'company_id': self.env.user.company_id.id})
        if 'currency_id' in fields:
            company_id = res.get('company_id') or False
            if company_id:
                company = self.env['res.company'].browse(company_id)
                currency_id = company.on_change_country(company.country_id.id)['value']['currency_id']
                res.update({'currency_id': currency_id})

        chart_templates = account_chart_template.search([('visible', '=', True)])
        if chart_templates:
            #in order to set default chart which was last created set max of ids.
            chart_id = max(chart_templates.ids)
            if context.get("default_charts"):
                model_data = self.env['ir.model.data'].search_read([('model', '=', 'account.chart.template'),
                                                                    ('module', '=', context.get("default_charts"))],
                                                                   ['res_id'])
                if model_data:
                    chart_id = model_data[0]['res_id']
            chart = account_chart_template.browse(chart_id)
            chart_hierarchy_ids = self._get_chart_parent_ids(chart)
            if 'chart_template_id' in fields:
                res.update({'only_one_chart_template': len(chart_templates) == 1,
                            'chart_template_id': chart_id})
            if 'sale_tax_id' in fields:
                sale_tax = tax_templ_obj.search([('chart_template_id', 'in', chart_hierarchy_ids),
                                                              ('type_tax_use', '=', 'sale')], limit=1, order='sequence')
                res.update({'sale_tax_id': sale_tax and sale_tax.id or False})
            if 'purchase_tax_id' in fields:
                purchase_tax = tax_templ_obj.search([('chart_template_id', 'in', chart_hierarchy_ids),
                                                                  ('type_tax_use', '=', 'purchase')], limit=1, order='sequence')
                res.update({'purchase_tax_id': purchase_tax and purchase_tax.id or False})
        res.update({
            'purchase_tax_rate': 15.0,
            'sale_tax_rate': 15.0,
        })
        return res

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        context = self._context or {}
        res = super(WizardChangeChartsAccounts, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=False)
        cmp_select = []
        CompanyObj = self.env['res.company']

        companies = CompanyObj.search([])
        #display in the widget selection of companies, only the companies that haven't been configured yet (but don't care about the demo chart of accounts)
        self._cr.execute("SELECT company_id FROM account_account WHERE deprecated = 'f' AND name != 'Chart For Automated Tests' AND name NOT LIKE '%(test)'")
        configured_cmp = [r[0] for r in self._cr.fetchall()]
        unconfigured_cmp = list(set(companies.ids) - set(configured_cmp))
        for field in res['fields']:
            if field == 'company_id':
                res['fields'][field]['domain'] = [('id', 'in', unconfigured_cmp)]
                res['fields'][field]['selection'] = [('', '')]
                if unconfigured_cmp:
                    cmp_select = [(line.id, line.name) for line in CompanyObj.browse(unconfigured_cmp)]
                    res['fields'][field]['selection'] = cmp_select
        return res

    def _create_tax_templates_from_rates(self, company_id):
        '''
        This function checks if the chosen chart template is configured as containing a full set of taxes, and if
        it's not the case, it creates the templates for account.tax object accordingly to the provided sale/purchase rates.
        Then it saves the new tax templates as default taxes to use for this chart template.

        :param company_id: id of the company for wich the wizard is running
        :return: True
        '''
        obj_tax_temp = self.env['account.tax.template']
        all_parents = self._get_chart_parent_ids(self.chart_template_id)
        # create tax templates from purchase_tax_rate and sale_tax_rate fields
        if not self.chart_template_id.complete_tax_set:
            value = self.sale_tax_rate
            ref_taxs = obj_tax_temp.search([('type_tax_use', '=', 'sale'), ('chart_template_id', 'in', all_parents)], order="sequence, id desc", limit=1)
            ref_taxs.write({'amount': value, 'name': _('Tax %.2f%%') % value, 'description': '%.2f%%' % value})
            value = self.purchase_tax_rate
            ref_taxs = obj_tax_temp.search([('type_tax_use', '=', 'purchase'), ('chart_template_id', 'in', all_parents)], order="sequence, id desc", limit=1)
            ref_taxs.write({'amount': value, 'name': _('Tax %.2f%%') % value, 'description': '%.2f%%' % value})
        return True

    def execute(self):
        '''
        This function is called at the confirmation of the wizard to generate the COA from the templates. It will read
        all the provided information to create the accounts, the banks, the journals, the taxes, the
        accounting properties... accordingly for the chosen company.
        '''

        #~ if len(self.env['account.account'].search([('company_id', '=', self.company_id.id)])) > 0:
            #~ # We are in a case where we already have some accounts existing, meaning that user has probably
            #~ # created its own accounts and does not need a coa, so skip installation of coa.
            #~ _logger.info('Could not install chart of account since some accounts already exists for the company (%s)', (self.company_id.id,))
            #~ return {}
        if not self.env.user._is_admin():
            raise AccessError(_("Only administrators can change the settings"))
        
        ir_values_obj = self.env['ir.values']
        company = self.company_id
        self.company_id.write({'currency_id': self.currency_id.id,
                               'accounts_code_digits': self.code_digits,
                               'anglo_saxon_accounting': self.use_anglo_saxon,
                               'bank_account_code_prefix': self.bank_account_code_prefix,
                               'cash_account_code_prefix': self.cash_account_code_prefix,
                               'chart_template_id': self.chart_template_id.id})

        #set the coa currency to active
        self.currency_id.write({'active': True})

        # When we install the CoA of first company, set the currency to price types and pricelists
        if company.id == 1:
            for reference in ['product.list_price', 'product.standard_price', 'product.list0']:
                try:
                    tmp2 = self.env.ref(reference).write({'currency_id': self.currency_id.id})
                except ValueError:
                    pass

        # If the floats for sale/purchase rates have been filled, create templates from them
        self._create_tax_templates_from_rates(company.id)

        # Install all the templates objects and generate the real objects
        acc_template_ref, taxes_ref = self.chart_template_id._install_template(company, code_digits=self.code_digits, transfer_account_id=self.transfer_account_id)

        # write values of default taxes for product as super user
        if self.sale_tax_id and taxes_ref:
            ir_values_obj.sudo().set_default('product.template', "taxes_id", [taxes_ref[self.sale_tax_id.id]], for_all_users=True, company_id=company.id)
        if self.purchase_tax_id and taxes_ref:
            ir_values_obj.sudo().set_default('product.template', "supplier_taxes_id", [taxes_ref[self.purchase_tax_id.id]], for_all_users=True, company_id=company.id)

        # Create Bank journals
        self._create_bank_journals_from_o2m(company, acc_template_ref)

        # Create the current year earning account if it wasn't present in the CoA
        account_obj = self.env['account.account']
        unaffected_earnings_xml = self.env.ref("account.data_unaffected_earnings")
        if unaffected_earnings_xml and not account_obj.search([('company_id', '=', company.id), ('user_type_id', '=', unaffected_earnings_xml.id)]):
            account_obj.create({
                'code': '999999',
                'name': _('Undistributed Profits/Losses'),
                'user_type_id': unaffected_earnings_xml.id,
                'company_id': company.id,})
        return {}

    def _create_bank_journals_from_o2m(self, company, acc_template_ref):
        '''
        This function creates bank journals and its accounts for each line encoded in the field bank_account_ids of the
        wizard (which is currently only used to create a default bank and cash journal when the CoA is installed).

        :param company: the company for which the wizard is running.
        :param acc_template_ref: the dictionary containing the mapping between the ids of account templates and the ids
            of the accounts that have been generated from them.
        '''
        self.ensure_one()
        _logger.warning('_create_bank_journals_from_o2m\ncompany: %s\nacc_template_ref: %s\n' % (company, acc_template_ref))
        # Create the journals that will trigger the account.account creation
        for acc in self.bank_account_ids:
            self.env['account.journal'].create({
                'name': acc.acc_name,
                'type': acc.account_type,
                'company_id': company.id,
                'currency_id': acc.currency_id.id,
                'sequence': 10
            })

class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    #~ @api.one
    #~ def try_loading_for_current_company(self):
        #~ self.ensure_one()
        #~ company = self.env.user.company_id
        #~ # If we don't have any chart of account on this company, install this chart of account
        #~ if not company.chart_template_id:
            #~ wizard = self.env['wizard.multi.charts.accounts'].create({
                #~ 'company_id': self.env.user.company_id.id,
                #~ 'chart_template_id': self.id,
                #~ 'code_digits': self.code_digits,
                #~ 'transfer_account_id': self.transfer_account_id.id,
                #~ 'currency_id': self.currency_id.id,
                #~ 'bank_account_code_prefix': self.bank_account_code_prefix,
                #~ 'cash_account_code_prefix': self.cash_account_code_prefix,
            #~ })
            #~ wizard.onchange_chart_template_id()
            #~ wizard.execute()

    #~ @api.multi
    #~ def open_select_template_wizard(self):
        #~ # Add action to open wizard to select between several templates
        #~ if not self.company_id.chart_template_id:
            #~ todo = self.env['ir.actions.todo']
            #~ action_rec = self.env['ir.model.data'].xmlid_to_object('account.action_wizard_multi_chart')
            #~ if action_rec:
                #~ todo.create({'action_id': action_rec.id, 'name': _('Choose Accounting Template'), 'type': 'automatic'})
        #~ return True

    @api.model
    def generate_journals(self, acc_template_ref, company, journals_dict=None):
        """
        This method is used for creating journals.

        :param chart_temp_id: Chart Template Id.
        :param acc_template_ref: Account templates reference.
        :param company_id: company_id selected from wizard.multi.charts.accounts.
        :returns: True
        """
        #~ _logger.warning('create_record_with_xmlid\ncompany: %s\ntemplate: %s\nmodel: %s\nvals: %s\nxmlid: %s\n' % (company, template, model, vals, template.get_metadata()[0].get('xmlid')))
        _logger.warning('generate_journals\nacc_template_ref: %s\ncompany: %s\njournals_dict: %s\n' % (acc_template_ref, company, journals_dict))
        
        JournalObj = self.env['account.journal']
        for vals_journal in self._prepare_all_journals(acc_template_ref, company, journals_dict=journals_dict):
            journal = JournalObj.search([('company_id', '=', company.id), ('code', '=', vals_journal['code'])])
            if journal:
                journal.write(vals_journal)
            else:
                journal = JournalObj.create(vals_journal)
            if vals_journal['type'] == 'general' and vals_journal['code'] == _('EXCH'):
                company.write({'currency_exchange_journal_id': journal.id})
        return True

    def _prepare_all_journals(self, acc_template_ref, company, journals_dict=None):
        def _get_default_account(journal_vals, type='debit'):
            # Get the default accounts
            default_account = False
            if journal['type'] == 'sale':
                default_account = acc_template_ref.get(self.property_account_income_categ_id.id)
            elif journal['type'] == 'purchase':
                default_account = acc_template_ref.get(self.property_account_expense_categ_id.id)
            elif journal['type'] == 'general' and journal['code'] == _('EXCH'):
                if type=='credit':
                    default_account = acc_template_ref.get(self.income_currency_exchange_account_id.id)
                else:
                    default_account = acc_template_ref.get(self.expense_currency_exchange_account_id.id)
            return default_account

        journals = [{'name': _('Customer Invoices'), 'type': 'sale', 'code': _('INV'), 'favorite': True, 'sequence': 5},
                    {'name': _('Vendor Bills'), 'type': 'purchase', 'code': _('BILL'), 'favorite': True, 'sequence': 6},
                    {'name': _('Miscellaneous Operations'), 'type': 'general', 'code': _('MISC'), 'favorite': False, 'sequence': 7},
                    {'name': _('Exchange Difference'), 'type': 'general', 'code': _('EXCH'), 'favorite': False, 'sequence': 9},]
        if journals_dict != None:
            journals.extend(journals_dict)

        self.ensure_one()
        journal_data = []
        for journal in journals:
            vals = {
                'type': journal['type'],
                'name': journal['name'],
                'code': journal['code'],
                'company_id': company.id,
                # 'default_credit_account_id': _get_default_account(journal, 'credit'),
                # 'default_debit_account_id': _get_default_account(journal, 'debit'),
                # 'show_on_dashboard': journal['favorite'],
                'sequence': journal['sequence']
            }
            journal_data.append(vals)
        return journal_data

    #~ @api.multi
    #~ def generate_properties(self, acc_template_ref, company):
        #~ """
        #~ This method used for creating properties.

        #~ :param self: chart templates for which we need to create properties
        #~ :param acc_template_ref: Mapping between ids of account templates and real accounts created from them
        #~ :param company_id: company_id selected from wizard.multi.charts.accounts.
        #~ :returns: True
        #~ """
        #~ self.ensure_one()
        #~ PropertyObj = self.env['ir.property']
        #~ todo_list = [
            #~ ('property_account_receivable_id', 'res.partner', 'account.account'),
            #~ ('property_account_payable_id', 'res.partner', 'account.account'),
            #~ ('property_account_expense_categ_id', 'product.category', 'account.account'),
            #~ ('property_account_income_categ_id', 'product.category', 'account.account'),
            #~ ('property_account_expense_id', 'product.template', 'account.account'),
            #~ ('property_account_income_id', 'product.template', 'account.account'),
        #~ ]
        #~ for record in todo_list:
            #~ account = getattr(self, record[0])
            #~ value = account and 'account.account,' + str(acc_template_ref[account.id]) or False
            #~ if value:
                #~ field = self.env['ir.model.fields'].search([('name', '=', record[0]), ('model', '=', record[1]), ('relation', '=', record[2])], limit=1)
                #~ vals = {
                    #~ 'name': record[0],
                    #~ 'company_id': company.id,
                    #~ 'fields_id': field.id,
                    #~ 'value': value,
                #~ }
                #~ properties = PropertyObj.search([('name', '=', record[0]), ('company_id', '=', company.id)])
                #~ if properties:
                    #~ #the property exist: modify it
                    #~ properties.write(vals)
                #~ else:
                    #~ #create the property
                    #~ PropertyObj.create(vals)
        #~ stock_properties = [
            #~ 'property_stock_account_input_categ_id',
            #~ 'property_stock_account_output_categ_id',
            #~ 'property_stock_valuation_account_id',
        #~ ]
        #~ for stock_property in stock_properties:
            #~ account = getattr(self, stock_property)
            #~ value = account and acc_template_ref[account.id] or False
            #~ if value:
                #~ company.write({stock_property: value})
        #~ return True

    def _install_template(self, company, code_digits=None, transfer_account_id=None, obj_wizard=None, acc_ref=None, taxes_ref=None):
        """ Recursively load the template objects and create the real objects from them.

            :param company: company the wizard is running for
            :param code_digits: number of digits the accounts code should have in the COA
            :param transfer_account_id: reference to the account template that will be used as intermediary account for transfers between 2 liquidity accounts
            :param obj_wizard: the current wizard for generating the COA from the templates
            :param acc_ref: Mapping between ids of account templates and real accounts created from them
            :param taxes_ref: Mapping between ids of tax templates and real taxes created from them
            :returns: tuple with a dictionary containing
                * the mapping between the account template ids and the ids of the real accounts that have been generated
                  from them, as first item,
                * a similar dictionary for mapping the tax templates and taxes, as second item,
            :rtype: tuple(dict, dict, dict)
        """
        self.ensure_one()
        if acc_ref is None:
            acc_ref = {}
        if taxes_ref is None:
            taxes_ref = {}
        if self.parent_id:
            tmp1, tmp2 = self.parent_id._install_template(company, code_digits=code_digits, transfer_account_id=transfer_account_id, acc_ref=acc_ref, taxes_ref=taxes_ref)
            acc_ref.update(tmp1)
            taxes_ref.update(tmp2)
        tmp1, tmp2 = self._load_template(company, code_digits=code_digits, transfer_account_id=transfer_account_id, account_ref=acc_ref, taxes_ref=taxes_ref)
        acc_ref.update(tmp1)
        taxes_ref.update(tmp2)
        return acc_ref, taxes_ref

    def _load_template(self, company, code_digits=None, transfer_account_id=None, account_ref=None, taxes_ref=None):
        """ Generate all the objects from the templates

            :param company: company the wizard is running for
            :param code_digits: number of digits the accounts code should have in the COA
            :param transfer_account_id: reference to the account template that will be used as intermediary account for transfers between 2 liquidity accounts
            :param acc_ref: Mapping between ids of account templates and real accounts created from them
            :param taxes_ref: Mapping between ids of tax templates and real taxes created from them
            :returns: tuple with a dictionary containing
                * the mapping between the account template ids and the ids of the real accounts that have been generated
                  from them, as first item,
                * a similar dictionary for mapping the tax templates and taxes, as second item,
            :rtype: tuple(dict, dict, dict)
        """
        self.ensure_one()
        if account_ref is None:
            account_ref = {}
        if taxes_ref is None:
            taxes_ref = {}
        if not code_digits:
            code_digits = self.code_digits
        if not transfer_account_id:
            # transfer_account_id = self.transfer_account_id
            transfer_account_id = self.property_account_receivable_id
        AccountTaxObj = self.env['account.tax']
        
        _logger.warning('\n\n=== Generating taxes ===\n\n')
        
        # Generate taxes from templates.
        generated_tax_res = self.tax_template_ids._generate_tax(company)
        taxes_ref.update(generated_tax_res['tax_template_to_tax'])

        # Generating Accounts from templates.
        account_template_ref = self.generate_account(taxes_ref, account_ref, code_digits, company)
        account_ref.update(account_template_ref)

        # writing account values after creation of accounts
        company.transfer_account_id = account_template_ref[transfer_account_id.id]
        for key, value in generated_tax_res['account_dict'].items():
            pass
            # print(value)
            # if value['refund_account_id'] or value['account_id']:
            #     AccountTaxObj.browse(key).write({
            #         'refund_account_id': account_ref.get(value['refund_account_id'], False),
            #         'account_id': account_ref.get(value['account_id'], False),
            #     })
        
        _logger.warning('\n\n=== Generating journals ===\n\n')
        
        # Create Journals - Only done for root chart template
        if not self.parent_id:
            self.generate_journals(account_ref, company)

        _logger.warning('\n\n=== Generating properties ===\n\n')
        
        # generate properties function
        self.generate_properties(account_ref, company)

        _logger.warning('\n\n=== Generating fiscal positions ===\n\n')
        
        # Generate Fiscal Position , Fiscal Position Accounts and Fiscal Position Taxes from templates
        self.generate_fiscal_position(taxes_ref, account_ref, company)

        _logger.warning('\n\n=== Generating account operation template templates ===\n\n')
        
        # Generate account operation template templates
        self.generate_account_reconcile_model(taxes_ref, account_ref, company)

        return account_ref, taxes_ref

    def create_record_with_xmlid(self, company, template, model, vals):
        # Create a record for the given model with the given vals and 
        # also create an entry in ir_model_data to have an xmlid for the newly created record
        # xmlid is the concatenation of company_id and template_xml_id
        ir_model_data = self.env['ir.model.data']
        template_xmlid = ir_model_data.search([('model', '=', template._name), ('res_id', '=', template.id)])
        xmlid = template_xmlid.module + '.' + template_xmlid.name
        _logger.warning('create_record_with_xmlid\ncompany: %s\ntemplate: %s\nmodel: %s\nvals: %s\nxmlid: %s\n' % (company, template, model, vals, xmlid))
        new_xml_id = str(company.id)+'_'+template_xmlid.name
        
        # Check for mapped ids
        mapped_id = self._context.get('change_chart_mapping', {}).get(model, {}).get(xmlid)
        if mapped_id:
            # Fix noupdate on existing xmlids
            noupdate = False
            old_xmlid = ir_model_data.search([('model', '=', model), ('res_id', '=', mapped_id)])
            for xmlid in old_xmlid:
                if xmlid.noupdate:
                    noupdate = True
                    xmlid.noupdate = False
            res = ir_model_data._update(model, template_xmlid.module, vals, xml_id=new_xml_id, store=True, noupdate=False, mode='update', res_id=mapped_id)
            # Restore noupdate if needed
            if noupdate:
                ir_model_data.search([('model', '=', model), ('res_id', '=', mapped_id)]).write({'noupdate': True})
            return res
        else:
            noupdate = False
            old_xmlid = ir_model_data.search([('module', '=', template_xmlid.module), ('name', '=', new_xml_id)])
            if old_xmlid:
                # Find all xmlids relating to this object.
                old_xmlid = ir_model_data.search([('model', '=', model), ('res_id', '=', old_xmlid.res_id)])
            else:
                # No matching xmlid found. Create a new one.
                return ir_model_data._update(model, template_xmlid.module, vals, xml_id=new_xml_id, store=True, noupdate=True, mode='init', res_id=False)
            # Fix noupdate on existing xmlids
            for xmlid in old_xmlid:
                if xmlid.noupdate:
                    noupdate = True
                    xmlid.noupdate = False
            # Existing xmlid found. Update it.
            res = ir_model_data._update(model, template_xmlid.module, vals, xml_id=new_xml_id, store=True, noupdate=False, mode='update', res_id=False)
            # Restore noupdate if needed
            if noupdate:
                ir_model_data.search([('model', '=', model), ('res_id', '=', mapped_id)]).write({'noupdate': True})
            return res

    @api.model
    def warninator(self, msg):
        _logger.warning(msg)
    #~ def _get_account_vals(self, company, account_template, code_acc, tax_template_ref):
        #~ """ This method generates a dictionnary of all the values for the account that will be created.
        #~ """
        #~ self.ensure_one()
        #~ tax_ids = []
        #~ for tax in account_template.tax_ids:
            #~ tax_ids.append(tax_template_ref[tax.id])
        #~ val = {
                #~ 'name': account_template.name,
                #~ 'currency_id': account_template.currency_id and account_template.currency_id.id or False,
                #~ 'code': code_acc,
                #~ 'user_type_id': account_template.user_type_id and account_template.user_type_id.id or False,
                #~ 'reconcile': account_template.reconcile,
                #~ 'note': account_template.note,
                #~ 'tax_ids': [(6, 0, tax_ids)],
                #~ 'company_id': company.id,
                #~ 'tag_ids': [(6, 0, [t.id for t in account_template.tag_ids])],
            #~ }
        #~ return val

    #~ @api.multi
    #~ def generate_account(self, tax_template_ref, acc_template_ref, code_digits, company):
        #~ """ This method for generating accounts from templates.

            #~ :param tax_template_ref: Taxes templates reference for write taxes_id in account_account.
            #~ :param acc_template_ref: dictionary with the mappping between the account templates and the real accounts.
            #~ :param code_digits: number of digits got from wizard.multi.charts.accounts, this is use for account code.
            #~ :param company_id: company_id selected from wizard.multi.charts.accounts.
            #~ :returns: return acc_template_ref for reference purpose.
            #~ :rtype: dict
        #~ """
        #~ self.ensure_one()
        #~ account_tmpl_obj = self.env['account.account.template']
        #~ acc_template = account_tmpl_obj.search([('nocreate', '!=', True), ('chart_template_id', '=', self.id)], order='id')
        #~ for account_template in acc_template:
            #~ code_main = account_template.code and len(account_template.code) or 0
            #~ code_acc = account_template.code or ''
            #~ if code_main > 0 and code_main <= code_digits:
                #~ code_acc = str(code_acc) + (str('0'*(code_digits-code_main)))
            #~ vals = self._get_account_vals(company, account_template, code_acc, tax_template_ref)
            #~ new_account = self.create_record_with_xmlid(company, account_template, 'account.account', vals)
            #~ acc_template_ref[account_template.id] = new_account
        #~ return acc_template_ref

    #~ def _prepare_reconcile_model_vals(self, company, account_reconcile_model, acc_template_ref, tax_template_ref):
        #~ """ This method generates a dictionnary of all the values for the account.reconcile.model that will be created.
        #~ """
        #~ self.ensure_one()
        #~ return {
                #~ 'name': account_reconcile_model.name,
                #~ 'sequence': account_reconcile_model.sequence,
                #~ 'has_second_line': account_reconcile_model.has_second_line,
                #~ 'company_id': company.id,
                #~ 'account_id': acc_template_ref[account_reconcile_model.account_id.id],
                #~ 'label': account_reconcile_model.label,
                #~ 'amount_type': account_reconcile_model.amount_type,
                #~ 'amount': account_reconcile_model.amount,
                #~ 'tax_id': account_reconcile_model.tax_id and tax_template_ref[account_reconcile_model.tax_id.id] or False,
                #~ 'second_account_id': account_reconcile_model.second_account_id and acc_template_ref[account_reconcile_model.second_account_id.id] or False,
                #~ 'second_label': account_reconcile_model.second_label,
                #~ 'second_amount_type': account_reconcile_model.second_amount_type,
                #~ 'second_amount': account_reconcile_model.second_amount,
                #~ 'second_tax_id': account_reconcile_model.second_tax_id and tax_template_ref[account_reconcile_model.second_tax_id.id] or False,
            #~ }

    #~ @api.multi
    #~ def generate_account_reconcile_model(self, tax_template_ref, acc_template_ref, company):
        #~ """ This method for generating accounts from templates.

            #~ :param tax_template_ref: Taxes templates reference for write taxes_id in account_account.
            #~ :param acc_template_ref: dictionary with the mappping between the account templates and the real accounts.
            #~ :param company_id: company_id selected from wizard.multi.charts.accounts.
            #~ :returns: return new_account_reconcile_model for reference purpose.
            #~ :rtype: dict
        #~ """
        #~ self.ensure_one()
        #~ account_reconcile_models = self.env['account.reconcile.model.template'].search([
            #~ ('account_id.chart_template_id', '=', self.id)
        #~ ])
        #~ for account_reconcile_model in account_reconcile_models:
            #~ vals = self._prepare_reconcile_model_vals(company, account_reconcile_model, acc_template_ref, tax_template_ref)
            #~ self.create_record_with_xmlid(company, account_reconcile_model, 'account.reconcile.model', vals)
        #~ return True

    #~ @api.multi
    #~ def generate_fiscal_position(self, tax_template_ref, acc_template_ref, company):
        #~ """ This method generate Fiscal Position, Fiscal Position Accounts and Fiscal Position Taxes from templates.

            #~ :param chart_temp_id: Chart Template Id.
            #~ :param taxes_ids: Taxes templates reference for generating account.fiscal.position.tax.
            #~ :param acc_template_ref: Account templates reference for generating account.fiscal.position.account.
            #~ :param company_id: company_id selected from wizard.multi.charts.accounts.
            #~ :returns: True
        #~ """
        #~ self.ensure_one()
        #~ positions = self.env['account.fiscal.position.template'].search([('chart_template_id', '=', self.id)])
        #~ for position in positions:
            #~ new_fp = self.create_record_with_xmlid(company, position, 'account.fiscal.position', {'company_id': company.id, 'name': position.name, 'note': position.note})
            #~ for tax in position.tax_ids:
                #~ self.create_record_with_xmlid(company, tax, 'account.fiscal.position.tax', {
                    #~ 'tax_src_id': tax_template_ref[tax.tax_src_id.id],
                    #~ 'tax_dest_id': tax.tax_dest_id and tax_template_ref[tax.tax_dest_id.id] or False,
                    #~ 'position_id': new_fp
                #~ })
            #~ for acc in position.account_ids:
                #~ self.create_record_with_xmlid(company, acc, 'account.fiscal.position.account', {
                    #~ 'account_src_id': acc_template_ref[acc.account_src_id.id],
                    #~ 'account_dest_id': acc_template_ref[acc.account_dest_id.id],
                    #~ 'position_id': new_fp
                #~ })
        #~ return True
