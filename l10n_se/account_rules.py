# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2017 Vertel AB (<http://vertel.se>).
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
import sys
sys.path.append('.')
sys.path.append('../')


class account_rules(object):


    def __init__(self):
        
        import account_rules_fields


        self.fields = account_rules_fields.fields

    #~ "data_account_type_receivable"
    #~ "data_account_type_payable"
    #~ "data_account_type_liquidity"
    #~ "data_account_type_credit_card"
    #~ "data_account_type_current_assets"
    #~ "data_account_type_non_current_assets"
    #~ "data_account_type_prepayments"
    #~ "data_account_type_fixed_assets"
    #~ "data_account_type_current_liabilities"
    #~ "data_account_type_non_current_liabilities"
    #~ "data_account_type_equity"
    #~ "data_unaffected_earnings"
    #~ "data_account_type_other_income"
    #~ "data_account_type_revenue"
    #~ "data_account_type_depreciation"
    #~ "data_account_type_expenses"
    #~ "data_account_type_direct_costs"

    def code2user_type_id(self, code):
        for l in self.fields:
            if code in l.get('k'):
                return l.get('ut')

    def code2tax_ids(self, code):
        pass

    def code2tag_ids(self, code):
        pass

    def code2reconcile(self, code):
        if int(code) in range(1500, 1600) or int(code) in range(2400, 2450) or int(code) == 1630:
            return True
        else:
            return False

    def code2note(self, code):
        for l in self.fields:
            if code in l.get('k'):
                return l.get('b')

    def code2field(self, code):
        for l in self.fields:
            if code in l.get('k'):
                return l.get('f')


if __name__ == '__main__':
    R = account_rules()
    print R.fields
