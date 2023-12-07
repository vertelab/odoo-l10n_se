# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import Warning, RedirectWarning, UserError
from odoo import http
import base64
from datetime import datetime
import odoo

import logging

_logger = logging.getLogger(__name__)


class MergeTaxesWizard(models.Model):
    _name = 'merge.taxes.wizard'
    _description = 'Merge Chart Wizard'

    @api.depends('current_chart', 'supplement_chart')
    def _merge_name(self):
        for rec in self:
            rec.name = f"{self.current_chart.name} - {self.supplement_chart.name}"

    @api.onchange("company_id")
    def get_current_chart_of_account(self):
        for record in self:
            record.current_chart = record.company_id.chart_template_id

    company_id = fields.Many2one('res.company', string='Current Company', default=lambda self: self.env.company)
    name = fields.Char(compute=_merge_name)
    current_chart = fields.Many2one('account.chart.template', string='Current Chart of Account', readonly=False,
                                    compute=get_current_chart_of_account)
    supplement_chart = fields.Many2one('account.chart.template', string='Supplement Chart of Account', required=True)
    missing_tax_line_ids = fields.One2many('merge.taxes', 'wizard_id', string='Missing Taxes')

    def _get_tax_template(self, account_chart_template_id):
        current_account_id = account_chart_template_id
        tax_template_ids = current_account_id.tax_template_ids

        while current_account_id.parent_id:
            current_account_id = current_account_id.parent_id
            tax_template_ids += current_account_id.parent_id.tax_template_ids

        return tax_template_ids

    def compare_and_list_missing_accounts(self):
        self.env['merge.taxes'].search([]).unlink()
        supplement_chart_tax_template_ids = self._get_tax_template(self.supplement_chart)

        for tax_template_id in supplement_chart_tax_template_ids:
            existing_tax_id = self.env['account.tax'].search(
                [('name', '=', tax_template_id.name), ('company_id', '=', self.company_id.id)])
            if not existing_tax_id:
                missing_tax_vals = {
                    'tax_template_id': tax_template_id.id,
                    'name': tax_template_id.name,
                    'wizard_id': self.id,
                }
                self.write({'missing_tax_line_ids': [(0, 0, missing_tax_vals)]})

    def create_missing_taxes(self):
        for missing_tax_line_id in self.missing_tax_line_ids:
            tax_template_id = missing_tax_line_id.tax_template_id

            existing_tax_id = self.env['account.tax'].search(
                [('name', '=', tax_template_id.name), ('company_id', '=', self.company_id.id)])

            if not existing_tax_id:
                missing_tax_vals = {
                    'name': tax_template_id.name,
                    'type_tax_use': tax_template_id.type_tax_use,
                    'active': tax_template_id.active,
                    'amount': tax_template_id.amount,
                    'amount_type': tax_template_id.amount_type,
                    'description': tax_template_id.description,
                    'is_base_affected': tax_template_id.is_base_affected,
                }
                existing_tax_id.create(missing_tax_vals)
        self.compare_and_list_missing_accounts()


class MissingTaxes(models.Model):
    _name = 'merge.taxes'
    _description = 'Merge Account Line'

    @api.model
    def default_user_type(self):
        return self.env.ref('account.data_account_type_fixed_assets')

    name = fields.Char(string='Name', required=False)
    tax_template_id = fields.Many2one('account.tax.template', string='Tax Template', required=True)
    wizard_id = fields.Many2one('merge.taxes.wizard', string='Wizard')


