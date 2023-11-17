# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import Warning, RedirectWarning, UserError
from odoo import http
import base64
from datetime import datetime
import odoo

import logging

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def return_merge_chart_wizard_action(self):
        action = self.env["ir.actions.actions"]._for_xml_id("l10n_se_extended.action_merge_chart_wizard")
        return action


class MergeChartWizard(models.Model):
    _name = 'merge.chart.wizard'
    _description = 'Merge Chart Wizard'

    @api.depends('current_chart', 'supplement_chart')
    def _merge_name(self):
        for rec in self:
            rec.name = f"{self.current_chart.name} - {self.supplement_chart.name}"

    @api.onchange("company_id")
    def get_current_chart_of_account(self):
        for record in self:
            # record.diff_account_line_ids_account_types = False
            # record.diff_account_line_ids_name = False
            # record.missing_account_line_ids = False
            record.current_chart = record.company_id.chart_template_id

    company_id = fields.Many2one('res.company', string='Current Company', default=lambda self: self.env.company)
    name = fields.Char(compute=_merge_name)
    current_chart = fields.Many2one('account.chart.template', string='Current Chart of Account', readonly=True,
                                    compute=get_current_chart_of_account)
    supplement_chart = fields.Many2one('account.chart.template', string='Supplement Chart of Account')
    missing_account_line_ids = fields.One2many('merge.account.account', 'wizard_id', string='New Accounts',
                                               domain=[('sort_type', '=', 'new_account')])

    diff_account_line_ids_name = fields.One2many(comodel_name='merge.account.account', inverse_name='wizard_id',
                                                 string='Accounts with different names',
                                                 domain=[('sort_type', '=', 'account_name_diff')])
    diff_account_line_ids_account_types = fields.One2many(comodel_name='merge.account.account',
                                                          inverse_name='wizard_id',
                                                          string='Accounts with different accounts',
                                                          domain=[('sort_type', '=', 'account_type_diff')])

    def _supplement_accounts(self):
        current_supplement_chart = self.supplement_chart
        all_account_template_from_supplement = current_supplement_chart.account_ids

        while current_supplement_chart.parent_id:
            current_supplement_chart = current_supplement_chart.parent_id
            all_account_template_from_supplement += current_supplement_chart.account_ids

        return all_account_template_from_supplement

    def _compute_missing_accounts(self):
        all_accounts_from_supplement = self._supplement_accounts()

        for account in all_accounts_from_supplement:
            existing_account = self.env['account.account'].search(
                [('code', '=', account.code), ('company_id', '=', self.company_id.id)])
            if not existing_account:
                missing_account_vals = {
                    'code': account.code,
                    'name': account.name,
                    'account_type': account.account_type,
                    'reconcile': account.reconcile,
                    'wizard_id': self.id,
                    'created': False,
                    'sort_type': 'new_account',
                }
                self.write({'missing_account_line_ids': [(0, 0, missing_account_vals)]})

    def compare_and_list_missing_accounts(self):
        self.env['merge.account.account'].search([]).unlink()
        self._compute_account_diff_names()
        self._compute_account_diff_types()
        self._compute_missing_accounts()

    def _compute_account_diff_names(self):
        all_account_template_from_supplement = self._supplement_accounts()
        # all_accounts_from_supplement = self._supplement_accounts()
        all_accounts_from_current = self.env['account.account'].search([])

        all_accounts_from_supplement = self.env['account.account']
        for account in all_account_template_from_supplement:
            all_accounts_from_supplement += self.env['account.account'].search(
                [('code', '=', account.code), ('company_id', '=', self.company_id.id)])

        for current_acc in all_accounts_from_current:
            for sup_acc in all_accounts_from_supplement:
                if ((current_acc.code == sup_acc.code)
                        and (current_acc.name.strip().casefold() != sup_acc.name.strip().casefold())):
                    vals = {
                        'code': sup_acc.code,
                        'name': sup_acc.name,
                        'account_type': sup_acc.account_type,
                        'reconcile': sup_acc.reconcile,
                        'current_name': current_acc.name,
                        'wizard_id': self.id,
                        'created': False,
                        'sort_type': 'account_name_diff',
                    }
                    self.write({'diff_account_line_ids_name': [(0, 0, vals)]})

    def _compute_account_diff_types(self):
        all_account_template_from_supplement = self._supplement_accounts()
        all_accounts_from_current = self.env['account.account'].search([])

        all_accounts_from_supplement = self.env['account.account']
        for account in all_account_template_from_supplement:
            all_accounts_from_supplement += self.env['account.account'].search(
                [('code', '=', account.code), ('company_id', '=', self.company_id.id)])

        for current_acc in all_accounts_from_current:
            for sup_acc in all_accounts_from_supplement:
                if ((current_acc.code == sup_acc.code)
                        and (current_acc.account_type.strip().casefold() != sup_acc.account_type.strip().casefold())):
                    vals = {
                        'code': sup_acc.code,
                        'name': sup_acc.name,
                        'account_type': sup_acc.account_type,
                        'reconcile': sup_acc.reconcile,
                        'current_name': current_acc.name,
                        'current_account_type': current_acc.account_type,
                        'wizard_id': self.id,
                        'created': False,
                        'sort_type': 'account_type_diff',
                    }
                    self.write({'diff_account_line_ids_name': [(0, 0, vals)]})

    def create_missing_accounts(self):
        for missing_account in self.missing_account_line_ids:
            self.env['account.account'].create({
                'code': missing_account.code,
                'name': missing_account.code,
                'account_type': missing_account.account_type,
                'reconcile': missing_account.reconcile,
            })
        self.self._compute_missing_accounts()


class MissingAccountLines(models.Model):
    _name = 'merge.account.account'
    _description = 'Merge Account Line'

    @api.model
    def default_user_type(self):
        return self.env.ref('account.data_account_type_fixed_assets')

    sort_type = fields.Selection(
        selection=[
            ("new_account", "New Account"),
            ("account_name_diff", "Account Different Name"),
            ("account_type_diff", "Account Different Types"),
        ],
        defualt="new_account",
        string="Sort Type",
        required=True
    )
    wizard_id = fields.Many2one('merge.chart.wizard', string='Wizard')
    created = fields.Boolean(string='')
    reconcile = fields.Boolean(string='')
    name = fields.Char(string='Name', required=False)
    code = fields.Char(string='Code', size=64, required=True)
    account_type = fields.Selection(
        selection=[
            ("asset_receivable", "Receivable"),
            ("asset_cash", "Bank and Cash"),
            ("asset_current", "Current Assets"),
            ("asset_non_current", "Non-current Assets"),
            ("asset_prepayments", "Prepayments"),
            ("asset_fixed", "Fixed Assets"),
            ("liability_payable", "Payable"),
            ("liability_credit_card", "Credit Card"),
            ("liability_current", "Current Liabilities"),
            ("liability_non_current", "Non-current Liabilities"),
            ("equity", "Equity"),
            ("equity_unaffected", "Current Year Earnings"),
            ("income", "Income"),
            ("income_other", "Other Income"),
            ("expense", "Expenses"),
            ("expense_depreciation", "Depreciation"),
            ("expense_direct_cost", "Cost of Revenue"),
            ("off_balance", "Off-Balance Sheet"),
        ],
        string="Type",
        required=False, readonly=False,
        help="Account Type is used for information purpose, to generate country-specific legal reports, and set the "
             "rules to close a fiscal year and generate opening entries."
    )

    current_reconcile = fields.Boolean(string="Current Reconcile")
    current_name = fields.Char(string='Current Name', required=False)
    current_account_type = fields.Selection(
        selection=[
            ("asset_receivable", "Receivable"),
            ("asset_cash", "Bank and Cash"),
            ("asset_current", "Current Assets"),
            ("asset_non_current", "Non-current Assets"),
            ("asset_prepayments", "Prepayments"),
            ("asset_fixed", "Fixed Assets"),
            ("liability_payable", "Payable"),
            ("liability_credit_card", "Credit Card"),
            ("liability_current", "Current Liabilities"),
            ("liability_non_current", "Non-current Liabilities"),
            ("equity", "Equity"),
            ("equity_unaffected", "Current Year Earnings"),
            ("income", "Income"),
            ("income_other", "Other Income"),
            ("expense", "Expenses"),
            ("expense_depreciation", "Depreciation"),
            ("expense_direct_cost", "Cost of Revenue"),
            ("off_balance", "Off-Balance Sheet"),
        ],
        string="Current Type",
        required=False, readonly=False,
        help="Account Type is used for information purpose, to generate country-specific legal reports, and set the "
             "rules to close a fiscal year and generate opening entries."
    )


