# coding: utf-8
# Copyright 2016 Vauxoo (https://www.vauxoo.com) <info@vauxoo.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import models, api, _


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    @api.model
    def generate_journals(self, acc_template_ref, company, journals_dict=None):
        """Set the tax_cash_basis_journal_id on the company"""
        res = super(AccountChartTemplate, self).generate_journals(
            acc_template_ref, company, journals_dict=journals_dict)
        if not self == self.env.ref('l10n_se.chart_template_k2_2017'):
            return res
        journal_basis = self.env['account.journal'].search([
            ('company_id', '=', company.id),
            ('type', '=', 'general'),
            ('code', '=', 'LÖN')], limit=1)
        company.write({'tax_cash_basis_journal_id': journal_basis.id})
        return res

    def _prepare_all_journals(self, acc_template_ref, company, journals_dict=None):
        """Create the tax_cash_basis_journal_id"""
        res = super(AccountChartTemplate, self)._prepare_all_journals(
            acc_template_ref, company, journals_dict=journals_dict)
        if not self == self.env.ref('l10n_se.chart_template_K2_2017'):
            return res
        account = acc_template_ref.get(self.env.ref('l10n_se.K1_1010_2017').id)
        res.append({
            'type': 'general',
            'name': _('Effectively Paid'),
            'code': 'LÖN',
            'company_id': company.id,
            'default_credit_account_id': account,
            'default_debit_account_id': account,
            'show_on_dashboard': True,
        })
        return res

    @api.model
    def _prepare_transfer_account_for_direct_creation(self, name, company):
        res = super(AccountChartTemplate, self)._prepare_transfer_account_for_direct_creation(name, company)
        if company.country_id.code == 'SE':
            xml_id = self.env.ref('l10n_se.tag_a').id
            res.setdefault('tag_ids', [])
            res['tag_ids'].append((4, xml_id))
        return res
