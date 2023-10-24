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
        # ~ action['res_id'] = self.id
        return action
        

class MergeChartWizard(models.TransientModel):
    _name = 'merge.chart.wizard'
    
    # ~ @api.depends('diff_account_line_ids'):
        
    
    @api.onchange("company_id")
    def get_current_chart_of_account(self):
        for record in self:
            record.diff_account_line_ids = False
            record.missing_account_line_ids = False
            record.current_chart = record.company_id.chart_template_id

    company_id = fields.Many2one('res.company', string='Current Company', default=lambda self: self.env.company)
    name = fields.Char()
    current_chart = fields.Many2one('account.chart.template', string='Current Chart of Account',readonly = True, compute=get_current_chart_of_account)
    supplement_chart = fields.Many2one('account.chart.template', string='Supplement Chart of Account')
    missing_account_line_ids = fields.One2many(comodel_name='merge.account.account', inverse_name='wizard_id', string='New Accounts')
    diff_account_line_ids = fields.One2many(comodel_name='merge.account.account', inverse_name='wizard_id2', string='Accounts with differences')
    diff_account_line_ids_name = fields.One2many(comodel_name='merge.account.account', inverse_name='wizard_id2', string='Accounts with different names', domain=[('name','!=','current_name')])
    diff_account_line_ids_account_types = fields.One2many(comodel_name='merge.account.account', inverse_name='wizard_id2', string='Accounts with different accounts', domain=['|',('account_type','!=','current_account_type'),('reconcile','!=','current_reconcile')])
    
    
    def compare_and_list_missing_accounts(self):
        self.diff_account_line_ids = False
        self.missing_account_line_ids = False
        missing_accounts = []
        diff_accounts = []
        
        #We don't know how many parents a chart of account has so here we gather all accounts from all parents
        current_supplement_chart = self.supplement_chart
        all_accounts_from_supplment = current_supplement_chart.account_ids
        while current_supplement_chart.parent_id:
            current_supplement_chart = current_supplement_chart.parent_id
            all_accounts_from_supplment = all_accounts_from_supplment + current_supplement_chart.account_ids
        
        for account in all_accounts_from_supplment:
            existing_account = self.env['account.account'].search([('code','=',account.code),('company_id','=',self.company_id.id)])
            if not existing_account:
               missing_accounts.append({
               'code':account.code,
               'name':account.name,
               'account_type':account.account_type,
               'reconcile':account.reconcile,
               'wizard_id':self.id,
               'created':False,
               })
            else:
                relevant_fields = ['code','name','account_type','reconcile']
                diff = False
                diffs = {'wizard_id2':self.id,'code':account.code}
                for relevant_field in relevant_fields:
                    if getattr(existing_account, relevant_field) != getattr(account, relevant_field):
                       diff = True
                       _logger.warning(f"{getattr(existing_account, relevant_field)=}")
                       _logger.warning(f"{getattr(account, relevant_field)=}")
                       diffs[relevant_field] = getattr(account, relevant_field)
                       diffs["current_"+relevant_field] = getattr(existing_account, relevant_field)
                if diff:
                   diff_accounts.append(diffs)
        _logger.warning(f"{missing_accounts=}")
        list1 = self.env['merge.account.account'].create(missing_accounts+diff_accounts)
        _logger.warning(f"{list1=}")
        action = self.env["ir.actions.actions"]._for_xml_id("l10n_se_extended.action_merge_chart_wizard")
        action['res_id'] = self.id
        return action


class chart_account_account(models.TransientModel):
    _name = 'merge.account.account'
    _description = 'Merge New Account Line'

    @api.model
    def default_user_type(self):
        return self.env.ref('account.data_account_type_fixed_assets')
        
    wizard_id = fields.Many2one(comodel_name='merge.chart.wizard', string='Wizard')
    wizard_id2 = fields.Many2one(comodel_name='merge.chart.wizard', string='Wizard')
    created = fields.Boolean(string='')
    reconcile = fields.Boolean(string='')
    name = fields.Char(string='Name', required=False, select=True)
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
        string="Type", tracking=True,
        required=False, readonly=False,
        help="Account Type is used for information purpose, to generate country-specific legal reports, and set the rules to close a fiscal year and generate opening entries."
    )
    
    
    current_reconcile = fields.Boolean(string='',String="Current Reconcile")
    current_name = fields.Char(string='Current Name', required=False, select=True)
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
        string="Current Type", tracking=True,
        required=False, readonly=False,
        help="Account Type is used for information purpose, to generate country-specific legal reports, and set the rules to close a fiscal year and generate opening entries."
    )
    
    
    # ~ parent_id = fields.Many2one(comodel_name='account.account', string='Parent', domain=[('type', '=', 'view')])
