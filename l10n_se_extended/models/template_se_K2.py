# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('chart_template_K2')
    def _get_se_template_data(self):
        return {
            'name': 'K2 - Små till medelstora verksamheter',
            'parent': 'chart_template_BASE',
            'code_digits': '4',
        }

    @template('chart_template_K2', 'res.company')
    def _get_se_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.se',
                'bank_account_code_prefix': 'K2513',
                'cash_account_code_prefix': 'K2516',
                'transfer_account_code_prefix': 'K2517',
                'income_currency_exchange_account_id': 'K2_7500_2017',
            },
        }
