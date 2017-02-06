# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
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

#~ import time
#~ from datetime import datetime
#~ from dateutil.relativedelta import relativedelta
#~ from operator import itemgetter

#~ from openerp import pooler
#~ from openerp.osv import fields, osv
#~ from openerp.tools.translate import _

from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
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

    
    def _create_bank_journals_from_o2m(self, cr, uid, obj_wizard, company_id, acc_template_ref, context=None):
        '''
        This function creates bank journals and its accounts for each line encoded in the field bank_accounts_id of the
        wizard.

        :param obj_wizard: the current wizard that generates the COA from the templates.
        :param company_id: the id of the company for which the wizard is running.
        :param acc_template_ref: the dictionary containing the mapping between the ids of account templates and the ids
            of the accounts that have been generated from them.
        :return: True
        '''
        obj_acc = self.pool.get('account.account')
        obj_journal = self.pool.get('account.journal')
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

    def default_get(self, cr, uid, fields, context=None):
        res = super(wizard_multi_charts_accounts, self).default_get(cr, uid, fields, context=context) 
        if 'bank_accounts_id' in fields:
            company_id = res.get('company_id') or False
            if company_id:
                company = self.pool.get('res.company').browse(cr, uid, company_id, context=context)
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
    
    
     #~ _columns = {
        #~ 'name': fields.char('Name', required=True, select=True),
        #~ 'currency_id': fields.many2one('res.currency', 'Secondary Currency', help="Forces all moves for this account to have this secondary currency."),
        #~ 'code': fields.char('Code', size=64, required=True, select=1),
        #~ 'type': fields.selection([
            #~ ('receivable','Receivable'),
            #~ ('payable','Payable'),
            #~ ('view','View'),
            #~ ('consolidation','Consolidation'),
            #~ ('liquidity','Liquidity'),
            #~ ('other','Regular'),
            #~ ('closed','Closed'),
            #~ ], 'Internal Type', required=True,help="This type is used to differentiate types with "\
            #~ "special effects in Odoo: view can not have entries, consolidation are accounts that "\
            #~ "can have children accounts for multi-company consolidations, payable/receivable are for "\
            #~ "partners accounts (for debit/credit computations), closed for depreciated accounts."),
        #~ 'user_type': fields.many2one('account.account.type', 'Account Type', required=True,
            #~ help="These types are defined according to your country. The type contains more information "\
            #~ "about the account and its specificities."),
        #~ 'financial_report_ids': fields.many2many('account.financial.report', 'account_template_financial_report', 'account_template_id', 'report_line_id', 'Financial Reports'),
        #~ 'reconcile': fields.boolean('Allow Reconciliation', help="Check this option if you want the user to reconcile entries in this account."),
        #~ 'shortcut': fields.char('Shortcut', size=12),
        #~ 'note': fields.text('Note'),
        #~ 'parent_id': fields.many2one('account.account.template', 'Parent Account Template', ondelete='cascade', domain=[('type','=','view')]),
        #~ 'child_parent_ids':fields.one2many('account.account.template', 'parent_id', 'Children'),
        #~ 'tax_ids': fields.many2many('account.tax.template', 'account_account_template_tax_rel', 'account_id', 'tax_id', 'Default Taxes'),
        #~ 'nocreate': fields.boolean('Optional create', help="If checked, the new chart of accounts will not contain this by default."),
        #~ 'chart_template_id': fields.many2one('account.chart.template', 'Chart Template', help="This optional field allow you to link an account template to a specific chart template that may differ from the one its root parent belongs to. This allow you to define chart templates that extend another and complete it with few new accounts (You don't need to define the whole structure that is common to both several times)."),
    #~ }    
     
        #~ account.account.template

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
