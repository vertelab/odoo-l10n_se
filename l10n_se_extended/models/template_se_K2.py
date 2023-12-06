# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('extended_se_K2')
    def _get_extended_se_K2_template_data(self):
        return {
            'name': 'K2 - Små till medelstora verksamheter',
            'parent': 'extended_se',
            'code_digits': '4',
        }

    @template('extended_se_K2', 'res.company')
    def _get_extended_se_K2_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.se',
                'bank_account_code_prefix': 'K2513',
                'cash_account_code_prefix': 'K2516',
                'transfer_account_code_prefix': 'K2517',
                'income_currency_exchange_account_id': 'a7500',
            },
        }
