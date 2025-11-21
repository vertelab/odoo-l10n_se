# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('kommun_bas_se')
    def _get_kommun_bas_se_template_data(self):
        return {
            'name': 'Swedish Kommun Bas',
            'property_account_receivable_id': 'a1158',
            'property_account_payable_id': 'a2421',
            'property_account_expense_categ_id': 'a401',
            'property_account_income_categ_id': 'a301',
            'account_sale_tax_id': 'sale_tax_25_goods',
            'account_purchase_tax_id': 'purchase_tax_25_goods',
            'code_digits': 2,
        }

    @template('kommun_bas_se', 'res.company')
    def _get_kommun_bas_se_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.se',
                'bank_account_code_prefix': 'K2513',
                'cash_account_code_prefix': 'K2516',
                'transfer_account_code_prefix': 'K2517',
                'account_default_pos_receivable_account_id': 'a7841',
                'income_currency_exchange_account_id': 'a7841',

            },
        }