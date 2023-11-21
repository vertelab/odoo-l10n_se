# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('chart_template_general')
    def _get_se_template_data(self):
        return {
            'property_account_receivable_id': 'chart1510',
            'property_account_payable_id': 'chart2440',
            'property_account_expense_categ_id': 'chart8990',
            'property_account_income_categ_id': 'chart3004',
            #'property_stock_account_input_categ_id': 'TODO',
            #'property_stock_account_output_categ_id': 'TODO',
            #'property_stock_valuation_account_id': 'TODO',
            #'property_tax_payable_account_id': 'TODO',
            #'property_tax_receivable_account_id': 'TODO',
            'code_digits': '4',
        }

    @template('chart_template_general', 'res.company')
    def _get_se_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.se',
                'bank_account_code_prefix': 'K2513',
                'cash_account_code_prefix': 'K2516',
                'transfer_account_code_prefix': 'K2517',
                'account_default_pos_receivable_account_id': 'chart1910',
                #'income_currency_exchange_account_id': 'K2_7500_2017', #??
                #'expense_currency_exchange_account_id': 'chart1910',
                #'account_journal_early_pay_discount_loss_account_id': 'TODO',
                #'account_journal_early_pay_discount_gain_account_id': 'TODO',
                #'account_sale_tax_id': 'TODO',
                #'account_purchase_tax_id': 'TODO',
            },
        }
