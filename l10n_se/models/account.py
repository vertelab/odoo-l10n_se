# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2004-2017 Vertel (<http://vertel.se>).
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

import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from operator import itemgetter

from openerp.osv import osv

from odoo import models, fields, api, _
from odoo.exceptions import except_orm, Warning, RedirectWarning
import base64
from odoo.tools.safe_eval import safe_eval as eval

try:
    from xlrd import open_workbook
except ImportError:
    raise Warning('excel library missing, pip install xlrd')

import logging
_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    type = fields.Selection(selection_add=[('bg', 'Bankgiro'), ('pg', 'Plusgiro')], ondelete = {'bg':'cascade','pg':'cascade'})
    

class AccountChartTemplate(models.Model):
    _inherit = 'account.account'

    @api.model
    def fix_account_types(self):
        current_year_earnings = self.env.ref('account.data_unaffected_earnings')
        current_year_earnings.write({"name":'Current Year Earnings'})
        current_year_earnings.write({"account_range":"[('code', 'in', [])]"})
        current_year_earnings.write({"account_range":False})
        for t in self.env['account.account.type'].search([]):
            if t.account_range:
                for a in self.env['account.account'].search(eval(t.account_range)):
                    if a.user_type_id != t:
                       a.user_type_id = t
                       _logger.warn('Account %s set type to %s' %(a.name, t.name))


    
# class account_bank_accounts_wizard(models.TransientModel):
#     _inherit = 'account.bank.accounts.wizard'
#
#     account_type = fields.Selection(selection_add=[('bg', 'Bankgiro'), ('pg', 'Plusgiro')])


class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    tax_balance_ids = fields.One2many('account.fiscal.position.tax.balance', 'position_id', string='Tax Balance Mapping', copy=True)

    # ~ @api.multi
    def get_map_balance_row(self, values):
        if not values.get('tax_line_id'):
            return
        tax = None
        for line in self.tax_balance_ids.filtered(lambda r: r.tax_src_id.id == values['tax_line_id']):
            tax = line.tax_dest_id
        if tax:
            return {
                'invoice_tax_line_id': values.get('invoice_tax_line_id'), # ??? Looks like it does nothing
                'tax_line_id': tax.id,
                'type': 'tax',
                'name': values.get('name'),
                'price_unit': values.get('price_unit'),
                'quantity': values.get('quantity'),
                'price': -values.get('price', 0), # debit (+) or credit (-)
                'account_id': tax.account_id and tax.account_id.id,
                'account_analytic_id': values.get('account_analytic_id'),
                'invoice_id': values.get('invoice_id'),
                'tax_ids': values.get('tax_ids'), # Looks like it will contain any previous taxes that will be included in the base value for this tax
            }


class AccountFiscalPositionTaxBalance(models.Model):
    _name = 'account.fiscal.position.tax.balance'
    _description = 'Taxes Balance Fiscal Position'
    _rec_name = 'position_id'

    position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position',
        required=True, ondelete='cascade')
    tax_src_id = fields.Many2one('account.tax', string='Tax on Product', required=True)
    tax_dest_id = fields.Many2one('account.tax', string='Tax to Balance Against', required=True)

    _sql_constraints = [
        ('tax_src_dest_uniq',
         'unique (position_id,tax_src_id)',
         'A tax balance fiscal position could be defined only one time on same taxes.')
    ]


class AccountFiscalPositionTemplate(models.Model):
    _inherit = 'account.fiscal.position.template'

    tax_balance_ids = fields.One2many('account.fiscal.position.tax.balance.template', 'position_id', string='Tax Balance Mapping', copy=True)
    auto_apply = fields.Boolean(string='Detect Automatically', help="Apply automatically this fiscal position.")
    vat_required = fields.Boolean(string='VAT required', help="Apply only if partner has a VAT number.")
    country_id = fields.Many2one('res.country', string='Country',
        help="Apply only if delivery or invoicing country match.")
    country_group_id = fields.Many2one('res.country.group', string='Country Group',
        help="Apply only if delivery or invocing country match the group.")


class AccountFiscalPositionTaxBalanceTemplate(models.Model):
    _name = 'account.fiscal.position.tax.balance.template'
    _description = 'Taxes Balance Fiscal Position'
    _rec_name = 'position_id'

    position_id = fields.Many2one('account.fiscal.position.template', string='Fiscal Position',
        required=True, ondelete='cascade')
    tax_src_id = fields.Many2one('account.tax.template', string='Tax on Product', required=True)
    tax_dest_id = fields.Many2one('account.tax.template', string='Tax to Balance Against', required=True)

    _sql_constraints = [
        ('tax_src_dest_uniq',
         'unique (position_id,tax_src_id)',
         'A tax balance fiscal position could be defined only one time on same taxes.')
    ]


class AccountInvoice(models.Model):
    # ~ _inherit = 'account.invoice'
    _inherit = 'account.move'
    
    @api.depends('company_id', 'invoice_filter_type_domain')
    def _compute_suitable_journal_ids(self):
        for m in self:
            journal_type = m.invoice_filter_type_domain
            company_id = m.company_id.id or self.env.company.id
            if journal_type:
                domain = [('company_id', '=', company_id), ('type', '=', journal_type)]
            else:
                domain = [('company_id', '=', company_id)]
            m.suitable_journal_ids = self.env['account.journal'].search(domain)

    # ~ OLD function to add balance taxes, this function no longer exists in account.move, which is why it never gets called.
    # ~ @api.model
    # ~ def tax_line_move_line_get(self):
        # ~ res = super(AccountInvoice, self).tax_line_move_line_get()
        # ~ if not self.fiscal_position_id:
            # ~ return res
        # ~ i = 0
        # ~ while i < len(res):
            # ~ values = self.fiscal_position_id.get_map_balance_row(res[i])
            # ~ _logger.warn('values: %s' % values)
            # ~ if values:
                # ~ i += 1
                # ~ res.insert(i, values)
            # ~ i += 1
        # ~ _logger.warn('res: %s' % res)
        # ~ return res

# ~ inherited override a function from accoung.move, due to the fact that we sometimes need to add extra journal lines based on account.fisical.postion and the tax used for that line.

    def action_post(self):
        # ~ When the user presses post then we add the balance lines here if needed.
        # ~ Skatte område/Fiscal Position
        fiscal_position = self.fiscal_position_id
        # ~ _logger.warning("jakmar: skatteområde: {} id:{}".format(self.fiscal_position_id.name, self.fiscal_position_id.id))
        
        # ~ Balance map for the current fiscal postition
        tax_balance_map_ids = self.fiscal_position_id.tax_balance_ids
        tax_balance_dict = {}
        for tax_balance_map_id in tax_balance_map_ids:
            src_tax = tax_balance_map_id.tax_src_id
            dest_tax = tax_balance_map_id.tax_dest_id
            
            tax_balance_dict[src_tax.name] = dest_tax
            # ~ _logger.warning("jakmar: tax src: {}, tax dest: {}".format(src_tax.name, dest_tax.name))
        
        for move_line in self.line_ids:
            # ~ _logger.warning(f"jakmar line name:{move_line.name} tax: {move_line.tax_line_id.name}")
            # ~ Check if a tax balance exists
            if move_line.tax_line_id.name in tax_balance_dict:
                vals ={
                'name': f'Balance tax line: From: {move_line.tax_line_id.name} To: {tax_balance_dict[move_line.tax_line_id.name].name}', 
                'move_id':move_line.move_id.id,
                'currency_id':move_line.currency_id.id,
                'account_id':tax_balance_dict[move_line.tax_line_id.name].invoice_repartition_line_ids.account_id.id,
                'exclude_from_invoice_tab':True,
                'credit':move_line.debit
                }
                context_copy = self.env.context.copy()
                context_copy.update({'check_move_validity':False})
                new_line = self.with_context(context_copy).env['account.move.line'].create(vals)  
                new_line.write({'tax_line_id':tax_balance_dict[move_line.tax_line_id.name].id})# ~ won't set the correct tax_line_id if i try to set it during create
                self.with_context(context_copy)._recompute_dynamic_lines()
                
        # ~ end of my added code
        self._post(soft=False)
        return False
        
        




# class wizard_multi_charts_accounts(models.TransientModel):
#     """
#         defaults for 4 digits in chart of accounts
#      """
#     _inherit = 'wizard.multi.charts.accounts'
#
#     code_digits = fields.Integer(default=4)
    # bank_accounts_id = fields.One2many(comodel_name='account.bank.accounts.wizard', inverse_name='bank_account_id',
    #                                    string='Cash and Banks', help="Bank (och kontant) som även har journal",
    #                                    required=True)

    # @api.multi
    # def execute(self):
    #     res = super(wizard_multi_charts_accounts, self).execute()
    #     loner_till_tjansteman_7210 = self.env['account.account'].search([('code', '=', '7210')])
    #     lon_vaxa_stod_tjansteman = self.env['account.account'].search([('code', '=', '7213')])
    #     loner_till_tjansteman_16_36 = self.env['account.account'].search([('code', '=', '7214')])
    #     loner_till_tjansteman_6_15 = self.env['account.account'].search([('code', '=', '7215')])
    #     avrakning_lagstadgade_sociala_avgifter = self.env['account.account'].search([('code', '=', '2731')])
    #     avrakning_sarskild_loneskatt = self.env['account.account'].search([('code', '=', '2732')])
    #     personalskatt = self.env['account.account'].search([('code', '=', '2710')])
    #     account_values = {
    #         'UlagAvgHel': {'account_id': loner_till_tjansteman_7210.id, 'refund_account_id': loner_till_tjansteman_7210.id},
    #         'UlagVXLon': {'account_id': lon_vaxa_stod_tjansteman.id, 'refund_account_id': lon_vaxa_stod_tjansteman.id},
    #         'UlagAvgAldersp': {'account_id': loner_till_tjansteman_16_36.id, 'refund_account_id': loner_till_tjansteman_16_36.id},
    #         'UlagAlderspSkLon': {'account_id': loner_till_tjansteman_6_15.id, 'refund_account_id': loner_till_tjansteman_6_15.id},
    #         'AvgHel': {'account_id': avrakning_lagstadgade_sociala_avgifter.id, 'refund_account_id': avrakning_lagstadgade_sociala_avgifter.id},
    #         'AvgVXLon': {'account_id': avrakning_sarskild_loneskatt.id, 'refund_account_id': avrakning_sarskild_loneskatt.id},
    #         'AvgAldersp': {'account_id': avrakning_lagstadgade_sociala_avgifter.id, 'refund_account_id': avrakning_lagstadgade_sociala_avgifter.id},
    #         'AvgAlderspSkLon': {'account_id': avrakning_lagstadgade_sociala_avgifter.id, 'refund_account_id': avrakning_lagstadgade_sociala_avgifter.id},
    #         'AgPre': {'account_id': personalskatt.id, 'refund_account_id': personalskatt.id},
    #         'SkAvdrLon': {'account_id': personalskatt.id, 'refund_account_id': personalskatt.id},
    #     }
    #     for k,v in account_values.items():
    #         self.env['account.tax'].search([('name', '=', k)]).write(v)
    #     return res
    #
    # def X_create_bank_journals_from_o2m(self, obj_wizard, company_id, acc_template_ref):
    #     '''
    #     This function creates bank journals and its accounts for each line encoded in the field bank_accounts_id of the
    #     wizard.
    #
    #     :param obj_wizard: the current wizard that generates the COA from the templates.
    #     :param company_id: the id of the company for which the wizard is running.
    #     :param acc_template_ref: the dictionary containing the mapping between the ids of account templates and the ids
    #         of the accounts that have been generated from them.
    #     :return: True
    #     '''
    #     obj_acc = self.env['account.account']
    #     obj_journal = self.env['account.journal']
    #     code_digits = obj_wizard.code_digits
    #
    #     # Build a list with all the data to process
    #     journal_data = []
    #     if obj_wizard.bank_accounts_id:
    #         for acc in obj_wizard.bank_accounts_id:
    #             vals = {
    #                 'acc_name': acc.acc_name,
    #                 'account_type': acc.account_type,
    #                 'currency_id': acc.currency_id.id,
    #             }
    #             journal_data.append(vals)
    #     ref_acc_bank = obj_wizard.chart_template_id.bank_account_view_id
    #     if journal_data and not ref_acc_bank.code:
    #         raise osv.except_osv(_('Configuration Error !'), _('The bank account defined on the selected chart of accounts hasn\'t a code.'))
    #
    #     current_num = 1
    #     for line in journal_data:
    #         # Seek the next available number for the account code
    #         while True:
    #             new_code = str(ref_acc_bank.code[0:code_digits-len(str(current_num))].ljust(code_digits-len(str(current_num)), '0')) + str(current_num)
    #             ids = obj_acc.search([('code', '=', new_code), ('company_id', '=', company_id)])
    #             if not ids:
    #                 break
    #             else:
    #                 current_num += 1
    #         # Create the default debit/credit accounts for this bank journal
    #         vals = self._prepare_bank_account(line, new_code, acc_template_ref, ref_acc_bank, company_id)
    #         default_account_id = obj_acc.create(vals)
    #
    #         #create the bank journal
    #         vals_journal = self._prepare_bank_journal(line, current_num, default_account_id, company_id)
    #         obj_journal.create(vals_journal)
    #         current_num += 1
    #     return True
    #
    # @api.model
    # def default_get(self, fields):
    #     res = super(wizard_multi_charts_accounts, self).default_get(fields)
    #     if 'bank_accounts_id' in fields:
    #         company_id = res.get('company_id') or False
    #         if company_id:
    #             company = self.env['res.company'].browse(company_id)
    #             ba_list = [{'acc_name': _('Kalle Cash'), 'account_type': 'cash'}]
    #             for ba in company.bank_ids:
    #                 ba_list += [{'acc_name': ba.acc_number, 'account_type': ba.acc_type}]
    #             res.update({'bank_account_id': ba_list})
    #     return res


class account_chart_template(models.Model):
    """
        defaults for 4 digits in chart of accounts
     """
    _inherit = 'account.chart.template'

    code_digits = fields.Integer(default=4)
    bas_sru = fields.Binary(string="BAS SRU")
    bas_chart = fields.Binary(string="BAS Chart of Account")
    bas_k2 = fields.Boolean(string='Ej K2', default=True)
    bas_basic = fields.Boolean(string='Endast grundläggande konton',default=True)

    @api.onchange('bas_chart')
    def update_bas_chart(self):
        if not self.bas_chart:
            return

        wb = open_workbook(file_contents=base64.decodestring(self.bas_chart))
        ws = wb.sheet_by_index(0)
        basic_code = u' \u25a0'
        not_k2 = u'[Ej K2]'

        nbr_lines = ws.nrows
        user_type = 'account.data_account_type_asset'

        _logger.warn('Accounts %s' % self.env['account.account.template'].search([('code', 'like', '%.0')]))
        self.env['account.account.template'].search([('code', 'like', '%.0')]).unlink()

        # return
        for l in range(0, ws.nrows):
            if ws.cell_value(l, 2) == 1 or ws.cell_value(l, 2) in range(10, 20) or ws.cell_value(l, 2) in range(1000, 1999):
                user_type = 'account.data_account_type_asset'
            if ws.cell_value(l, 2) in range(15,26) or ws.cell_value(l,2) in range(1500,1599) :
                user_type = 'account.data_account_type_receivable'
            if ws.cell_value(l, 2) in range(1900,1999):
                user_type = 'account.data_account_type_bank'
            if ws.cell_value(l,2) == 1910:
                user_type = 'account.data_account_type_cash'

            if ws.cell_value(l,2) == 2 or ws.cell_value(l,2) in range(20,30) or ws.cell_value(l,2) in range(2000,2999) :
                    user_type = 'account.data_account_type_liability'
            if ws.cell_value(l,2) == 20 or ws.cell_value(l,2) in range(2000,2050):
                    user_type = 'account.conf_account_type_equity'
            if ws.cell_value(l,2) in [23,24] or ws.cell_value(l,2) in range(2300,2700):
                    user_type = 'account.data_account_type_payable'
            if ws.cell_value(l,2) in [26,27] or ws.cell_value(l,2) in range(2600,2800):
                    user_type = 'account.conf_account_type_tax'

            if ws.cell_value(l,2) == 3 or ws.cell_value(l,2) == '30-34'  or ws.cell_value(l,2) in range(30,40) or ws.cell_value(l,2) in range(3000,4000):
                    user_type = 'account.data_account_type_income'
            if ws.cell_value(l,2) in [4,5,6,7] or ws.cell_value(l,2) in ['5-6'] or  ws.cell_value(l,2) in range(30,80) or ws.cell_value(l,2) in ['40-45'] or ws.cell_value(l,2) in range(4000,8000):
                    user_type = 'account.data_account_type_expense'


            if ws.cell_value(l,2) == 8 or ws.cell_value(l,2) in [80,81,82,83] or ws.cell_value(l,2) in range(8000,8400):
                    user_type = 'account.data_account_type_income'
            if ws.cell_value(l,2) in [84,88] or ws.cell_value(l,2) in range(8400,8500) or ws.cell_value(l,2) in range(8800,8900):
                    user_type = 'account.data_account_type_expense'
            if ws.cell_value(l,2) in [89] or ws.cell_value(l,2) in range(8900,9000):
                    user_type = 'account.data_account_type_expense'

            if ws.cell_value(l,2) in range(1,9) or ws.cell_value(l,2) in ['5-6']: # kontoklass
                last_account_class = self.env['account.account.template'].create({
                    'code': ws.cell_value(l,2),
                    'name': ws.cell_value(l,3),
                    'user_type': self.env.ref(user_type).id,
                    'type': 'view',
                    'chart_template_id': self.id,
                  })
            if ws.cell_value(l, 2) in range(10,99) or ws.cell_value(l,2) in ['30-34','40-45']: # kontogrupp
                last_account_group = self.env['account.account.template'].create(
                    {
                        'code': ws.cell_value(l,2),
                        'name': ws.cell_value(l,3),
                        'type': 'view',
                        'user_type': self.env.ref(user_type).id,
                        'parent_id':last_account_class.id,
                        'chart_template_id': self.id,
                        })

            if ws.cell_value(l,2) in range(1000,9999):
                last_account = self.env['account.account.template'].create({
                    'code': ws.cell_value(l,2),
                    'name': ws.cell_value(l,3),
                    'type': 'other',
                    'parent_id':last_account_group.id,
                    'user_type': self.env.ref(user_type).id,
                    'chart_template_id': self.id,
                    'bas_k34': True if  ws.cell_value(l,1) == not_k2 else False,
                    'bas_basic': True if ws.cell_value(l,1) == basic_code else False,
                    })
                if ws.cell_value(l,5) in range(1000,9999):
                    last_account = self.env['account.account.template'].create({
                        'code': ws.cell_value(l,5),
                        'name': ws.cell_value(l,6),
                        'type': 'other',
                        'parent_id':last_account_group.id,
                        'user_type': self.env.ref(user_type).id,
                        'chart_template_id': self.id,
                        'bas_k34': True if  ws.cell_value(l, 4) == not_k2 else False,
                        'bas_basic': True if ws.cell_value(l, 4) == basic_code else False,
                        })

            #~ if ws.cell_value(l,1) == basic_code and self.bas_basic:
                #~ _logger.warn("%s %s" % (ws.cell_value(l,2),ws.cell_value(l,3)))
                #~ for account_l in range(l,ws.nrows):
                    #~ if ws.cell_value(l,4) == basic_code:
                        #~ _logger.warn("%s %s" % (ws.cell_value(l,5),ws.cell_value(l,6)))
                    #~ if ws.cell_value(l,2) > 0:
                        #~ break

    # ~ @api.multi
    def generate_fiscal_position(self, tax_template_ref, acc_template_ref, company):
        """ This method generate Fiscal Position, Fiscal Position Accounts and Fiscal Position Taxes from templates.

            :param chart_temp_id: Chart Template Id.
            :param taxes_ids: Taxes templates reference for generating account.fiscal.position.tax.
            :param acc_template_ref: Account templates reference for generating account.fiscal.position.account.
            :param company_id: company_id selected from wizard.multi.charts.accounts.
            :returns: True
        """
        res = super(account_chart_template, self).generate_fiscal_position(tax_template_ref, acc_template_ref, company)
        positions = self.env['account.fiscal.position.template'].search([('chart_template_id', '=', self.id)])
        for position in positions:
            template_xmlid = self.env['ir.model.data'].search([('model', '=', position._name), ('res_id', '=', position.id)])
            new_xmlid = 'l10n_se.' + str(company.id) + '_' + template_xmlid.name
            new_fp = self.env.ref(new_xmlid)
            for balance in position.tax_balance_ids:
                self.create_record_with_xmlid(company, balance, 'account.fiscal.position.tax.balance', {
                    'tax_src_id': tax_template_ref[balance.tax_src_id.id],
                    'tax_dest_id': balance.tax_dest_id and tax_template_ref[balance.tax_dest_id.id] or False,
                    'position_id': new_fp.id
                })
            new_fp.auto_apply = position.auto_apply
            new_fp.vat_required = position.vat_required
            new_fp.country_id = position.country_id
            new_fp.country_group_id = position.country_group_id
        return res


class account_account_template(models.Model):
    _inherit = "account.account.template"

    bas_k34 = fields.Boolean(string='K3/K4', default=False)
    bas_basic = fields.Boolean(string='Endast grundläggande konton', default=True)

    # def account2group(self, account_code):
    #     if ws.cell_value(l,2) in range(1,9) or ws.cell_value(l,2) in [u'5–6']: # kontoklass
    #         last_account_class = self.env['account.account.template'].create({
    #             'code': str(int(ws.cell_value(l,2))) if isinstance( ws.cell_value(l,2), float ) else ws.cell_value(l,2),
    #             'name': ws.cell_value(l,3),
    #             'user_type': self.env['account.account.type'].account2user_type(ws.cell_value(l,2)).id,
    #             'type': 'view',
    #             'chart_template_id': chart_template_titles.id,
    #             'parent_id':root_account.id,
    #           })
    #     if ws.cell_value(l,2) in range(10,99) or ws.cell_value(l,2) in [u'30–34 Huvudintäkter',u"""40–45 """]: # kontogrupp
    #         last_account_group = self.env['account.account.template'].create({
    #                 'code': str(int(ws.cell_value(l,2))) if isinstance( ws.cell_value(l,2), float ) else ws.cell_value(l,2),
    #                 'name': ws.cell_value(l,3),
    #                 'type': 'view',
    #                 'user_type': self.env['account.account.type'].account2user_type(ws.cell_value(l,2)).id,
    #                 'parent_id':last_account_class.id,
    #                 'chart_template_id': chart_template_titles.id,
    #             })
    #
    #     return self.env.ref(user_type) if user_type else None

class account_tax_template(models.Model):
    _inherit = 'account.tax.template'

    def account2tax_ids(self,account_code):
        tax_ids = []
#        if user_type == 'account.data_account_type_income':
        if  account_code in range(3000,3670):
            tax_ids = [(6,0,[self.env['account.tax.template'].search([('description','=','MP1')])[0].id])]
        if  account_code in [3002,3402]:
            tax_ids = [(6,0,[self.env['account.tax.template'].search([('description','=','MP2')])[0].id])]
        if  account_code in [3003,3403]:
            tax_ids = [(6,0,[self.env['account.tax.template'].search([('description','=','MP3')])[0].id])]
        if  account_code in [3004,3100,3105,3108,3404]:
            tax_ids = []
#        if user_type == 'account.data_account_type_expense':
        if  account_code in range(4000,4600):
            tax_ids = [(6,0,[self.env['account.tax.template'].search([('description','=','I')])[0].id])]
        if  account_code in [4516,4532,4536,4546]:
            tax_ids = [(6,0,[self.env['account.tax.template'].search([('description','=','I12')])[0].id])]
        if  account_code in [4517,4533,4537,4547]:
            tax_ids = [(6,0,[self.env['account.tax.template'].search([('description','=','I6')])[0].id])]
        if  account_code in [4518,4538]:
            tax_ids = []
        if  account_code in range(5000,6600):
            tax_ids = [(6,0,[self.env['account.tax.template'].search([('description','=','I')])[0].id])]
        if  account_code in [5810]:
            tax_ids = [(6,0,[self.env['account.tax.template'].search([('description','=','I6')])[0].id])]
        return tax_ids

class account_account_type(models.Model):
    _inherit = 'account.account.type'

    name = fields.Char(string='Account Type', required=True, translate=False)
    element_name = fields.Char(string='Element Name', help='This name is used as tag in xbrl-file.')
    account_range = fields.Char(string='Accoun Range', help='Domain shows which account should has this account type.')
    main_type = fields.Selection(selection=[
        ('RorelsensIntakterLagerforandringarMmAbstract', u'Rörelseintäkter, lagerförändringar m.m.'),
        ('RorelsekostnaderAbstract', u'Rörelsekostnader'),
        ('FinansiellaPosterAbstract', u'Finansiella poster'),
        ('BokslutsdispositionerAbstract', u'Bokslutsdispositioner'),
        ('SkatterAbstract', u'Skatter'),
        ('TillgangarAbstract', u'Tillgångar'),
        ('EgetKapitalSkulderAbstract', u'Eget kapital och skulder'),
    ], string='Main Type')
    report_type = fields.Selection(selection=[('r', u'Resultaträkning'), ('b', u'Balansräkning')], string='Report Type')

    # key: element_name
    # value: name
    name_exchange_dict = {
        'Kundfordringar': u'Kundfordringar',
        'Leverantorsskulder': u'Leverantörsskulder',
        'KassaBankExklRedovisningsmedel': u'Kassa och bank exklusive redovisningsmedel',
        'CheckrakningskreditKortfristig': u'Kortfristig checkräkningskredit',
        'OvrigaFordringarKortfristiga': u'Övriga kortfristga fordringar',
        'KoncessionerPatentLicenserVarumarkenLiknandeRattigheter': u'Koncessioner, patent, licenser, varumärken samt liknande rättigheter',
        'ForskottFranKunder': u'Förskott från kunder',
        'MaskinerAndraTekniskaAnlaggningar': u'Maskiner och andra tekniska anläggningar',
        'OvrigaKortfristigaSkulder': u'Övriga kortfristiga skulder',
        'OvrigaLangfristigaSkulderKreditinstitut': u'Övriga långfristiga skulder till kreditinstitut',
        'Aktiekapital': u'Aktiekapital',
        'AretsResultat': u'Årets resultat',
        'OvrigaRorelseintakter': u'Övriga rörelseintäkter',
        'Nettoomsattning': u'Nettoomsättning',
        'AvskrivningarNedskrivningarMateriellaImmateriellaAnlaggningstillgangar': u'Av- och nedskrivningar av materiella och immateriella anläggningstillgångar',
        'OvrigaRorelsekostnader': u'Övriga rörelsekostnader',
        'HandelsvarorKostnader': u'Kostnad för sålda handelsvaror',
    }

    # Change account type names from core(account)
    @api.model
    def _change_name(self):
        for k,v in self.name_exchange_dict.items():
            self.env['account.account.type'].search([('element_name', '=', k)]).write({'name': v})
                 
    @api.model
    def set_account_type(self):
        _logger.warning("jakmar set_account_type")
        for record in self:
            for account in self.env['account.account'].search(eval(record.account_range)):
                if account.user_type_id != record:
                   account.user_type_id = record
                   _logger.warn('Account %s set type to %s' %(account.name, record.name))

    @api.model
    def return_eval(self):
        return eval

        # for action:
        # ~ o = env['account.account.type'].browse([9])
        # ~ ids = [a['id'] for a in env['account.account'].search_read([('user_type_id', 'in', [a.id for a in o])], ['id'])]
        # ~ sql = "UPDATE account_account SET reconcile = true WHERE id IN %s;"
        # ~ env.cr.execute(sql, [tuple(ids)])
        # ~ o.write({'type': 'payable'})

    # ~ @api.multi
    def get_account_range(self):
        self.ensure_one()
        return self.env['account.account'].search(eval(self.account_range))

    def account2user_type(self,account_code):
        user_type = 'account.data_account_type_asset'
        if account_code == 1 or account_code in range(10,20) or account_code in range(1000,1999) :
            user_type = 'account.data_account_type_asset'
        if account_code in range(15,26) or account_code in range(1500,1599) :
            user_type = 'account.data_account_type_receivable'
        if account_code in range(1900,1999):
            user_type = 'account.data_account_type_bank'
        if account_code == 1910:
            user_type = 'account.data_account_type_cash'

        if account_code == 2 or account_code in range(20,30) or account_code in range(2000,2999) :
                user_type = 'account.data_account_type_liability'
        if account_code == 20 or account_code in range(2000,2050):
                user_type = 'account.conf_account_type_equity'
        if account_code in [23,24] or account_code in range(2300,2700):
                user_type = 'account.data_account_type_payable'
        if account_code in [26,27] or account_code in range(2600,2800):
                user_type = 'account.conf_account_type_tax'

        if account_code == 3 or account_code == '30-34'  or account_code in range(30,40) or account_code in range(3000,4000):
                user_type = 'account.data_account_type_income'
        if account_code in [4,5,6,7] or account_code in ['5-6'] or  account_code in range(30,80) or account_code in ['40-45'] or account_code in range(4000,8000):
                user_type = 'account.data_account_type_expense'


        if account_code == 8 or account_code in [80,81,82,83] or account_code in range(8000,8400):
                user_type = 'account.data_account_type_income'
        if account_code in [84,88] or account_code in range(8400,8500) or account_code in range(8800,8900):
                user_type = 'account.data_account_type_expense'
        if account_code in [89] or account_code in range(8900,9000):
                user_type = 'account.data_account_type_expense'
        return self.env.ref(user_type) if user_type else None


# class account_financial_report(models.Model):
#     _inherit = 'account.financial.report'
#
#     element_name = fields.Char(string='Element Name', help='This name is used as tag in xbrl-file.')
#     version_name = fields.Char(string='Version Name', help='This name is from import file.')


class Company(models.Model):
    _inherit = 'res.company'

    @api.model
    def account_chart_func(self):
        # ~ company = self.env.ref('base.main_company')
        company = self.env.user.company_id
        if not company.chart_template_id:
            sek = self.env.ref('base.SEK')
            sek.active = True
            self.env.currency_id = sek
            config = self.env['res.config.settings'].create({})
            config.chart_template_id = self.env.ref('l10n_se.chart_template_K2_2017')
            config.chart_template_id.try_loading()
            config.set_values()
            year = datetime.today().strftime("%Y")
            fy = self.env['account.fiscalyear'].create({
                'name': year,
                'code': year,
                'date_start': '%s-01-01' % year,
                'date_stop': '%s-12-31' % year,
                'state': 'draft',
            })
            fy.create_period1()



class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'
    def _load(self, sale_tax_rate, purchase_tax_rate, company):
            _logger.warning("jakmar! load before super")
            res = super(AccountChartTemplate, self)._load(sale_tax_rate, purchase_tax_rate, company)
            _logger.warning("jakmar! load after super")
            loner_till_tjansteman_7210 = self.env['account.account'].search([('code', '=', '7210')])
            lon_vaxa_stod_tjansteman = self.env['account.account'].search([('code', '=', '7213')])
            loner_till_tjansteman_16_36 = self.env['account.account'].search([('code', '=', '7214')])
            loner_till_tjansteman_6_15 = self.env['account.account'].search([('code', '=', '7215')])
            avrakning_lagstadgade_sociala_avgifter = self.env['account.account'].search([('code', '=', '2731')])
            avrakning_sarskild_loneskatt = self.env['account.account'].search([('code', '=', '2732')])
            personalskatt = self.env['account.account'].search([('code', '=', '2710')])
            account_values = {
                'UlagAvgHel': {'invoice_repartition_line_ids':  [(5,0,0),(0, 0, {'factor_percent': 100,'repartition_type': 'base',}),(0,0, { 'factor_percent': 100,'repartition_type': 'tax','account_id': loner_till_tjansteman_7210.id,}),], 'refund_repartition_line_ids': [(5,0,0),(0, 0, { 'factor_percent': 100,'repartition_type': 'base', }),(0,0, {'factor_percent': 100,'repartition_type': 'tax','account_id': loner_till_tjansteman_7210.id, }),]},
                'UlagVXLon': {'invoice_repartition_line_ids': [(5,0,0),(0, 0, {'factor_percent': 100,'repartition_type': 'base',}),(0,0, { 'factor_percent': 100,'repartition_type': 'tax','account_id': lon_vaxa_stod_tjansteman.id,}),], 'refund_repartition_line_ids': [(5,0,0),(0, 0, {'factor_percent': 100,'repartition_type': 'base',}),(0,0, {'factor_percent': 100,'repartition_type': 'tax','account_id': lon_vaxa_stod_tjansteman.id, }),]},
                'UlagAvgAldersp': {'invoice_repartition_line_ids':[(5,0,0),(0, 0, {'factor_percent': 100,'repartition_type': 'base',}),(0,0, { 'factor_percent': 100,'repartition_type': 'tax','account_id': loner_till_tjansteman_16_36.id,}),], 'refund_repartition_line_ids':[(5,0,0),(0, 0, {'factor_percent': 100,'repartition_type': 'base',}),(0,0, { 'factor_percent': 100,'repartition_type': 'tax','account_id': loner_till_tjansteman_16_36.id,}),]},
                'UlagAlderspSkLon': {'invoice_repartition_line_ids':[(5,0,0),(0, 0, {'factor_percent': 100,'repartition_type': 'base',}),(0,0, { 'factor_percent': 100,'repartition_type': 'tax','account_id': loner_till_tjansteman_6_15.id,}),], 'refund_repartition_line_ids':[(5,0,0),(0, 0, {'factor_percent': 100,'repartition_type': 'base',}),(0,0, { 'factor_percent': 100,'repartition_type': 'tax','account_id': loner_till_tjansteman_6_15.id,}),]},
                'AvgHel': {'invoice_repartition_line_ids':[(5,0,0),(0, 0, {'factor_percent': 100,'repartition_type': 'base',}),(0,0, { 'factor_percent': 100,'repartition_type': 'tax','account_id': avrakning_lagstadgade_sociala_avgifter.id,}),], 'refund_repartition_line_ids':[(5,0,0),(0, 0, {'factor_percent': 100,'repartition_type': 'base',}),(0,0, { 'factor_percent': 100,'repartition_type': 'tax','account_id': avrakning_lagstadgade_sociala_avgifter.id,}),]},
                'AvgVXLon': {'invoice_repartition_line_ids':[(5,0,0),(0, 0, {'factor_percent': 100,'repartition_type': 'base',}),(0,0, { 'factor_percent': 100,'repartition_type': 'tax','account_id': avrakning_sarskild_loneskatt.id,}),], 'refund_repartition_line_ids':[(5,0,0),(0, 0, {'factor_percent': 100,'repartition_type': 'base',}),(0,0, { 'factor_percent': 100,'repartition_type': 'tax','account_id': avrakning_sarskild_loneskatt.id,}),]},
                'AvgAldersp': {'invoice_repartition_line_ids':[(5,0,0),(0, 0, {'factor_percent': 100,'repartition_type': 'base',}),(0,0, { 'factor_percent': 100,'repartition_type': 'tax','account_id': avrakning_lagstadgade_sociala_avgifter.id,}),], 'refund_repartition_line_ids':[(5,0,0),(0, 0, {'factor_percent': 100,'repartition_type': 'base',}),(0,0, { 'factor_percent': 100,'repartition_type': 'tax','account_id': avrakning_lagstadgade_sociala_avgifter.id,}),]},
                'AvgAlderspSkLon': {'invoice_repartition_line_ids':[(5,0,0),(0, 0, {'factor_percent': 100,'repartition_type': 'base',}),(0,0, { 'factor_percent': 100,'repartition_type': 'tax','account_id': avrakning_lagstadgade_sociala_avgifter.id,}),], 'refund_repartition_line_ids': [(5,0,0),(0, 0, {'factor_percent': 100,'repartition_type': 'base',}),(0,0, { 'factor_percent': 100,'repartition_type': 'tax','account_id': avrakning_lagstadgade_sociala_avgifter.id,}),]},
                'AgPre': {'invoice_repartition_line_ids':[(5,0,0),(0, 0, {'factor_percent': 100,'repartition_type': 'base',}),(0,0, { 'factor_percent': 100,'repartition_type': 'tax','account_id': personalskatt.id,}),], 'refund_repartition_line_ids':[(5,0,0),(0, 0, {'factor_percent': 100,'repartition_type': 'base',}),(0,0, { 'factor_percent': 100,'repartition_type': 'tax','account_id': personalskatt.id,}),]},
                'SkAvdrLon': {'invoice_repartition_line_ids':[(5,0,0),(0, 0, {'factor_percent': 100,'repartition_type': 'base',}),(0,0, { 'factor_percent': 100,'repartition_type': 'tax','account_id': personalskatt.id,}),], 'refund_repartition_line_ids':[(5,0,0),(0, 0, {'factor_percent': 100,'repartition_type': 'base',}),(0,0, { 'factor_percent': 100,'repartition_type': 'tax','account_id': personalskatt.id,}),]},
            }

            for k,v in account_values.items():
                self.env['account.tax'].search([('name', '=', k)]).write(v)
            return res
        

