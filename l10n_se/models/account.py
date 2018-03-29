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

try:
    from xlrd import open_workbook
except ImportError:
    raise Warning('excel library missing, pip install xlrd')

import logging
_logger = logging.getLogger(__name__)



class account_bank_accounts_wizard(models.TransientModel):
    _inherit='account.bank.accounts.wizard'

    account_type = fields.Selection(selection_add=[('bg','Bankgiro'),('pg','Plusgiro')])


class wizard_multi_charts_accounts(models.TransientModel):
    """
        defaults for 4 digits in chart of accounts
     """
    _inherit='wizard.multi.charts.accounts'

    code_digits = fields.Integer(default=4)
    bank_accounts_id = fields.One2many(comodel_name='account.bank.accounts.wizard',inverse_name='bank_account_id',string='Cash and Banks', help="Bank (och kontant) som även har journal",required=True)

    @api.multi
    def execute(self):
        res = super(wizard_multi_charts_accounts, self).execute()
        loner_till_tjansteman_7210 = self.env['account.account'].search([('code', '=', '7210')])
        lon_vaxa_stod_tjansteman = self.env['account.account'].search([('code', '=', '7213')])
        loner_till_tjansteman_16_36 = self.env['account.account'].search([('code', '=', '7214')])
        loner_till_tjansteman_6_15 = self.env['account.account'].search([('code', '=', '7215')])
        avrakning_lagstadgade_sociala_avgifter = self.env['account.account'].search([('code', '=', '2731')])
        avrakning_sarskild_loneskatt = self.env['account.account'].search([('code', '=', '2732')])
        personalskatt = self.env['account.account'].search([('code', '=', '2710')])
        account_values = {
            'UlagAvgHel': {'account_id': loner_till_tjansteman_7210.id, 'refund_account_id': loner_till_tjansteman_7210.id},
            'UlagVXLon': {'account_id': lon_vaxa_stod_tjansteman.id, 'refund_account_id': lon_vaxa_stod_tjansteman.id},
            'UlagAvgAldersp': {'account_id': loner_till_tjansteman_16_36.id, 'refund_account_id': loner_till_tjansteman_16_36.id},
            'UlagAlderspSkLon': {'account_id': loner_till_tjansteman_6_15.id, 'refund_account_id': loner_till_tjansteman_6_15.id},
            'AvgHel': {'account_id': avrakning_lagstadgade_sociala_avgifter.id, 'refund_account_id': avrakning_lagstadgade_sociala_avgifter.id},
            'AvgVXLon': {'account_id': avrakning_sarskild_loneskatt.id, 'refund_account_id': avrakning_sarskild_loneskatt.id},
            'AvgAldersp': {'account_id': avrakning_lagstadgade_sociala_avgifter.id, 'refund_account_id': avrakning_lagstadgade_sociala_avgifter.id},
            'AvgAlderspSkLon': {'account_id': avrakning_lagstadgade_sociala_avgifter.id, 'refund_account_id': avrakning_lagstadgade_sociala_avgifter.id},
            'AgPre': {'account_id': personalskatt.id, 'refund_account_id': personalskatt.id},
            'SkAvdrLon': {'account_id': personalskatt.id, 'refund_account_id': personalskatt.id},
        }
        for k,v in account_values.items():
            self.env['account.tax'].search([('name', '=', k)]).write(v)
        return res

    def X_create_bank_journals_from_o2m(self, obj_wizard, company_id, acc_template_ref):
        '''
        This function creates bank journals and its accounts for each line encoded in the field bank_accounts_id of the
        wizard.

        :param obj_wizard: the current wizard that generates the COA from the templates.
        :param company_id: the id of the company for which the wizard is running.
        :param acc_template_ref: the dictionary containing the mapping between the ids of account templates and the ids
            of the accounts that have been generated from them.
        :return: True
        '''
        obj_acc = self.env['account.account']
        obj_journal = self.env['account.journal']
        code_digits = obj_wizard.code_digits

        # Build a list with all the data to process
        journal_data = []
        if obj_wizard.bank_accounts_id:
            for acc in obj_wizard.bank_accounts_id:
                vals = {
                    'acc_name': acc.acc_name,
                    'account_type': acc.account_type,
                    'currency_id': acc.currency_id.id,
                }
                journal_data.append(vals)
        ref_acc_bank = obj_wizard.chart_template_id.bank_account_view_id
        if journal_data and not ref_acc_bank.code:
            raise osv.except_osv(_('Configuration Error !'), _('The bank account defined on the selected chart of accounts hasn\'t a code.'))

        current_num = 1
        for line in journal_data:
            # Seek the next available number for the account code
            while True:
                new_code = str(ref_acc_bank.code[0:code_digits-len(str(current_num))].ljust(code_digits-len(str(current_num)), '0')) + str(current_num)
                ids = obj_acc.search(cr, uid, [('code', '=', new_code), ('company_id', '=', company_id)])
                if not ids:
                    break
                else:
                    current_num += 1
            # Create the default debit/credit accounts for this bank journal
            vals = self._prepare_bank_account(cr, uid, line, new_code, acc_template_ref, ref_acc_bank, company_id, context=context)
            default_account_id  = obj_acc.create(cr, uid, vals, context=context)

            #create the bank journal
            vals_journal = self._prepare_bank_journal(cr, uid, line, current_num, default_account_id, company_id, context=context)
            obj_journal.create(cr, uid, vals_journal)
            current_num += 1
        return True

    @api.model
    def default_get(self, fields):
        res = super(wizard_multi_charts_accounts, self).default_get(fields)
        if 'bank_accounts_id' in fields:
            company_id = res.get('company_id') or False
            if company_id:
                company = self.env['res.company'].browse(company_id)
                ba_list = [{'acc_name': _('Kalle Cash'), 'account_type': 'cash'}]
                for ba in company.bank_ids:
                    ba_list += [{'acc_name': ba.acc_number, 'account_type': ba.state}]
                res.update({'bank_account_id': ba_list})
        return res

class account_chart_template(models.Model):
    """
        defaults for 4 digits in chart of accounts
     """
    _inherit='account.chart.template'

    code_digits = fields.Integer(default=4)
    bas_sru = fields.Binary(string="BAS SRU")
    bas_chart = fields.Binary(string="BAS Chart of Account")
    bas_k2 = fields.Boolean(string='Ej K2',default=True)
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

        #~ self.env['account.account.template'].search([('chart_template_id', '=',self.id),('code','>','1000'),('code','<','9999')]).unlink()
        #~ self.env['account.account.template'].search([('chart_template_id', '=',self.id),('code','>','10'),('code','<','99')]).unlink()
        #~ self.env['account.account.template'].search([('chart_template_id', '=',self.id),('code','>','1'),('code','<','9')]).unlink()
        #~ self.env['account.account.template'].search([('chart_template_id', '=',self.id)]).unlink()
        _logger.warn('Accounts %s' % self.env['account.account.template'].search([('code','like','%.0')]))
        self.env['account.account.template'].search([('code','like','%.0')]).unlink()
        #~ self.env['account.account.template'].search([('code','>','10'),('code','<','99')]).unlink()
        #~ self.env['account.account.template'].search([('code','>','1'),('code','<','9')]).unlink()
        #~ self.env['account.account.template'].search([]).unlink()

        return
        for l in range(0,ws.nrows):
            if ws.cell_value(l,2) == 1 or ws.cell_value(l,2) in range(10,20) or ws.cell_value(l,2) in range(1000,1999) :
                user_type = 'account.data_account_type_asset'
            if ws.cell_value(l,2) in range(15,26) or ws.cell_value(l,2) in range(1500,1599) :
                user_type = 'account.data_account_type_receivable'
            if ws.cell_value(l,2) in range(1900,1999):
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
            if ws.cell_value(l,2) in range(10,99) or ws.cell_value(l,2) in ['30-34','40-45']: # kontogrupp
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
                        'bas_k34': True if  ws.cell_value(l,4) == not_k2 else False,
                        'bas_basic': True if ws.cell_value(l,4) == basic_code else False,
                        })

            #~ if ws.cell_value(l,1) == basic_code and self.bas_basic:
                #~ _logger.warn("%s %s" % (ws.cell_value(l,2),ws.cell_value(l,3)))
                #~ for account_l in range(l,ws.nrows):
                    #~ if ws.cell_value(l,4) == basic_code:
                        #~ _logger.warn("%s %s" % (ws.cell_value(l,5),ws.cell_value(l,6)))
                    #~ if ws.cell_value(l,2) > 0:
                        #~ break


class account_account_template(models.Model):
    _inherit = "account.account.template"


    bas_k34 = fields.Boolean(string='K3/K4',default=False)
    bas_basic = fields.Boolean(string='Endast grundläggande konton',default=True)

    def account2group(self,account_code):
        if ws.cell_value(l,2) in range(1,9) or ws.cell_value(l,2) in [u'5–6']: # kontoklass
            last_account_class = self.env['account.account.template'].create({
                'code': str(int(ws.cell_value(l,2))) if isinstance( ws.cell_value(l,2), float ) else ws.cell_value(l,2),
                'name': ws.cell_value(l,3),
                'user_type': self.env['account.account.type'].account2user_type(ws.cell_value(l,2)).id,
                'type': 'view',
                'chart_template_id': chart_template_titles.id,
                'parent_id':root_account.id,
              })
        if ws.cell_value(l,2) in range(10,99) or ws.cell_value(l,2) in [u'30–34 Huvudintäkter',u"""40–
45 """]: # kontogrupp
            last_account_group = self.env['account.account.template'].create({
                    'code': str(int(ws.cell_value(l,2))) if isinstance( ws.cell_value(l,2), float ) else ws.cell_value(l,2),
                    'name': ws.cell_value(l,3),
                    'type': 'view',
                    'user_type': self.env['account.account.type'].account2user_type(ws.cell_value(l,2)).id,
                    'parent_id':last_account_class.id,
                    'chart_template_id': chart_template_titles.id,
                })

        return self.env.ref(user_type) if user_type else None

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

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
