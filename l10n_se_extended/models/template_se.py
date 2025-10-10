import logging
import os
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta

from odoo import models, api
from odoo.addons.account.models.chart_template import template

_logger = logging.getLogger(__name__)

class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

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
    
    def calc_fiscal_years(self,fiscal_year):
        fiscal_year_dt = parse(fiscal_year)

        last_year_end = fiscal_year_dt + relativedelta(months=1) - relativedelta(days=1)
        last_year_start = fiscal_year_dt - relativedelta(months=11)
        current_year_end = last_year_end + relativedelta(years=1)
        current_year_start = last_year_start + relativedelta(years=1)
        next_year_end = last_year_end + relativedelta(years=2)
        next_year_start = last_year_start + relativedelta(years=2)
        return {
            "last_year_end": last_year_end,
            "last_year_start": last_year_start,
            "current_year_end": current_year_end,
            "current_year_start": current_year_start,
            "next_year_end": next_year_end,
            "next_year_start": next_year_start
        }

    def create_fiscal_year(self,fiscal_year_start,fiscal_year_end):
        fiscal_year_name = fiscal_year_start.year
        if fiscal_year_start.year != fiscal_year_end.year:
            fiscal_year_name = f"{fiscal_year_start.year}-{fiscal_year_end.year}"
        if self.env["account.fiscalyear"].search([("name", "=", fiscal_year_name)]):
            return
        fiscal_year_id = self.env["account.fiscalyear"].create({"name": f"{fiscal_year_name}", "code": f"{fiscal_year_end.strftime("%G%m")}",  "date_start": fiscal_year_start, "date_stop": fiscal_year_end})
        fiscal_year_id.create_period1()

    api.model
    def try_load_k2(self):
        company_ids = self.env["res.company"].search([])
        fiscal_year = os.getenv("FISCAL_YEAR")
        _logger.info(f"{fiscal_year=}"*100)
        chart_template = "extended_se_K2"
        for company_id in company_ids:
            self.env["account.chart.template"].try_loading(chart_template,company_id)
            if fiscal_year:
                fiscal_year_dict = self.calc_fiscal_years(fiscal_year)
                self.create_fiscal_year(fiscal_year_dict["last_year_start"],fiscal_year_dict["last_year_end"])
                self.create_fiscal_year(fiscal_year_dict["current_year_start"],fiscal_year_dict["current_year_end"])
                self.create_fiscal_year(fiscal_year_dict["next_year_start"],fiscal_year_dict["next_year_end"])

