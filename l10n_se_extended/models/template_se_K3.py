# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('chart_template_K3')
    def _get_extended_se_K3_template_data(self):
        return {
            'name': 'K3 - Medelstora till större verksamheter',
            'parent': 'extended_se',
            'code_digits': '4',
        }

    @template('chart_template_K3', 'res.company')
    def _get_extended_se_K3_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.se',
                'bank_account_code_prefix': 'K2513',
                'cash_account_code_prefix': 'K2516',
                'transfer_account_code_prefix': 'K2517',
                'income_currency_exchange_account_id': 'a7500',
            },
        }
