# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    # @template('chart_template_general')
    @template('extended_se')
    def _get_extended_se_template_data(self):
        return {
            'property_account_receivable_id': 'a1510',
            'property_account_payable_id': 'a2440',
            'property_account_expense_categ_id': 'a8990',
            'property_account_income_categ_id': 'a3004',
            'property_stock_account_input_categ_id': 'a4960',
            'property_stock_account_output_categ_id': 'a4960',
            'property_stock_valuation_account_id': 'a1410',
            'property_tax_payable_account_id': 'a2650',
            'property_tax_receivable_account_id': 'a1650',
            'code_digits': '4',
        }

    @template('extended_se', 'res.company')
    def _get_extended_se_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.se',
                'bank_account_code_prefix': 'K2513',
                'cash_account_code_prefix': 'K2516',
                'transfer_account_code_prefix': 'K2517',
                'account_default_pos_receivable_account_id': 'a1910',
                'income_currency_exchange_account_id': 'a1910', #??
            },
        }
