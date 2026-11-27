# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('kommun_bas_se')
    def _get_kommun_bas_se_template_data(self):
        return {
            'name': 'Swedish Kommun Bas',
            # 151 Kundfordringar — the previous value a1158 pointed at
            # "Ackumulerade nedskrivningar, övriga fastighet", a write-down
            # account, not a receivable.
            'property_account_receivable_id': 'a151',
            # 251 Leverantörsskulder — a2421 is "Obligationsprogram och
            # förlagslån, kortfristig del", a loan account.
            'property_account_payable_id': 'a251',
            # 410 Anläggnings- och underhållsmaterial — a401 is "Inköp av
            # finansiella anläggnings- och omsättningstillgångar", an
            # investment account, not a running expense.
            'property_account_expense_categ_id': 'a410',
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
                'bank_account_code_prefix': '192',
                'cash_account_code_prefix': '191',
                'transfer_account_code_prefix': '195',
                'account_default_pos_receivable_account_id': 'a7841',
                'income_currency_exchange_account_id': 'a7841',

            },
        }