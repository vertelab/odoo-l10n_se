# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2011 Vertel (<http://vertel.se>).
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

from openerp import pooler
from openerp.osv import fields, osv
from openerp.tools.translate import _


class account_bank_accounts_wizard(osv.osv_memory):
    _name='account.bank.accounts.wizard'
    _inherit='account.bank.accounts.wizard'

    _columns = {
        'account_type': fields.selection([('cash','Cash'), ('bank','Bankkonto'),('bg','Bankgiro'),('pg','Plusgiro'),], 'Account Type', size=12),
    }

account_bank_accounts_wizard()




class wizard_multi_charts_accounts(osv.osv_memory):
    """
        defaults for 4 digits in chart of accounts
     """
    _name='wizard.multi.charts.accounts'
    _inherit='wizard.multi.charts.accounts'

    _columns = {
        'bank_accounts_id': fields.one2many('account.bank.accounts.wizard', 'bank_account_id', 'Cash and Banks', help="Bank (och kontant) som även har journal",required=True),
    }

    _defaults = {
        'code_digits': 4,
    }

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


wizard_multi_charts_accounts()

class account_chart_template(osv.osv):
    _inherit='account.chart.template'
    _name="account.chart.template"
    _description= "Templates for Account Chart"

    _defaults = {
        'code_digits': 4,
    }

account_chart_template()




# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
