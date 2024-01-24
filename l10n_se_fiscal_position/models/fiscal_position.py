# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2004-2017 Vertel (<http://vertel.se>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from operator import itemgetter

# from openerp.osv import osv

from odoo import models, fields, api, _, exceptions
from odoo.exceptions import except_orm, Warning, RedirectWarning, UserError, ValidationError

import base64
from odoo.tools.safe_eval import safe_eval as eval

try:
    from xlrd import open_workbook
except ImportError:
    raise Warning('excel library missing, pip install xlrd')

import logging

_logger = logging.getLogger(__name__)

class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    tax_balance_ids = fields.One2many('account.fiscal.position.tax.balance', 'position_id',
                                      string='Tax Balance Mapping', copy=True)

    # ~ @api.multi
    def get_map_balance_row(self, values):
        if not values.get('tax_line_id'):
            return
        tax = None
        for line in self.tax_balance_ids.filtered(lambda r: r.tax_src_id.id == values['tax_line_id']):
            tax = line.tax_dest_id
        if tax:
            return {
                'invoice_tax_line_id': values.get('invoice_tax_line_id'),  # ??? Looks like it does nothing
                'tax_line_id': tax.id,
                'type': 'tax',
                'name': values.get('name'),
                'price_unit': values.get('price_unit'),
                'quantity': values.get('quantity'),
                'price': -values.get('price', 0),  # debit (+) or credit (-)
                'account_id': tax.account_id and tax.account_id.id,
                'account_analytic_id': values.get('account_analytic_id'),
                'invoice_id': values.get('invoice_id'),
                'tax_ids': values.get('tax_ids'),
                # Looks like it will contain any previous taxes that will be included in the base value for this tax
            }

    def fix_old_tax_config(self):
        _logger.warning(self)
        for record in self:
            _logger.warning(record)
            for line in record.tax_balance_ids:
                _logger.warning(line)
                tax_src = line.tax_src_id
                _logger.warning(f"{tax_src=}")
                dest_tax = line.tax_dest_id
                _logger.warning(f"dest {dest_tax.name}")
                dest_account_id = ""

                for line in dest_tax.invoice_repartition_line_ids:
                    if line.account_id:
                        dest_account_id = line.account_id
                        break

                # ~ _logger.warning(f"{dest_tax_reperation=}")
                already_added = False
                # ~ _logger.warning(f"{dest_account_id=}")

                for account in tax_src.invoice_repartition_line_ids.mapped("account_id"):
                    if account == dest_account_id:
                        already_added = True
                    # ~ _logger.warning(f"{account}")
                # ~ _logger.warning(f"{already_added}")

                if not already_added:
                    val = {"factor_percent": -100, "repartition_type": "tax", "account_id": dest_account_id.id}
                    # ~ _logger.warning(f"{val}")
                    tax_src.write(
                        {"invoice_repartition_line_ids": [(0, 0, val)], 'refund_repartition_line_ids': [(0, 0, val)]})
                    # ~ _logger.warning(f"{dest_tax.name}")
                # ~ tax_src.write("invoice_repartition_line_ids":[(4,dest_tax,0)])


class AccountFiscalPositionTaxBalance(models.Model):
    _name = 'account.fiscal.position.tax.balance'
    _description = 'Taxes Balance Fiscal Position'
    _rec_name = 'position_id'

    position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position',
                                  required=True, ondelete='cascade')
    tax_src_id = fields.Many2one('account.tax', string='Tax on Product', required=True)
    tax_dest_id = fields.Many2one('account.tax', string='Tax to Balance Against', required=True)

    _sql_constraints = [
        ('tax_src_dest_uniq',
         'unique (position_id,tax_src_id)',
         'A tax balance fiscal position could be defined only one time on same taxes.')
    ]


class AccountFiscalPositionTemplate(models.Model):
    _inherit = 'account.fiscal.position.template'

    tax_balance_ids = fields.One2many('account.fiscal.position.tax.balance.template', 'position_id',
                                      string='Tax Balance Mapping', copy=True)
    auto_apply = fields.Boolean(string='Detect Automatically', help="Apply automatically this fiscal position.")
    vat_required = fields.Boolean(string='VAT required', help="Apply only if partner has a VAT number.")
    country_id = fields.Many2one('res.country', string='Country',
                                 help="Apply only if delivery or invoicing country match.")
    country_group_id = fields.Many2one('res.country.group', string='Country Group',
                                       help="Apply only if delivery or invocing country match the group.")


class AccountFiscalPositionTaxBalanceTemplate(models.Model):
    _name = 'account.fiscal.position.tax.balance.template'
    _description = 'Taxes Balance Fiscal Position'
    _rec_name = 'position_id'

    position_id = fields.Many2one('account.fiscal.position.template', string='Fiscal Position',
                                  required=True, ondelete='cascade')
    tax_src_id = fields.Many2one('account.tax.template', string='Tax on Product', required=True)
    tax_dest_id = fields.Many2one('account.tax.template', string='Tax to Balance Against', required=True)

    _sql_constraints = [
        ('tax_src_dest_uniq',
         'unique (position_id,tax_src_id)',
         'A tax balance fiscal position could be defined only one time on same taxes.')
    ]


class AccountInvoice(models.Model):
    # ~ _inherit = 'account.invoice'
    _inherit = 'account.move'

    def set_correct_orignator_tax_lines(self):
        for move in self:
            fiscal_position = move.fiscal_position_id
            for line in move.line_ids:
                line.set_correct_orignator_tax_line(fiscal_position)

class AccountMoveLine(models.Model):
        _inherit = 'account.move.line'

        @api.onchange('account_id')
        def _compute_mapped_fiscal_position_account(self):
            for line in self:
                if line.move_id.fiscal_position_id:
                    line.account_id = line.move_id.fiscal_position_id.map_account(line.account_id)

        @api.depends('tax_repartition_line_id.invoice_tax_id', 'tax_repartition_line_id.refund_tax_id')
        def _compute_tax_line_id(self):
            """ tax_line_id is computed as the tax linked to the repartition line creating
            the move.
            """
            for record in self:
                rep_line = record.tax_repartition_line_id
                # A constraint on account.tax.repartition.line ensures both those fields are mutually exclusive
                record.tax_line_id = rep_line.invoice_tax_id or rep_line.refund_tax_id

            for record in self:
                record.set_correct_orignator_tax_line()

        def set_correct_orignator_tax_line(self, fiscal_position_id=False):
            if not fiscal_position_id:
                fiscal_position_id = self.move_id.fiscal_position_id

            if fiscal_position_id and self.tax_line_id:
                tax_balance_map_ids = fiscal_position_id.tax_balance_ids
                tax_balance_dict = {}
                for tax_balance_map_id in tax_balance_map_ids:
                    src_tax = tax_balance_map_id.tax_src_id
                    dest_tax = tax_balance_map_id.tax_dest_id
                    tax_balance_dict[src_tax.name] = dest_tax

                dest_tax = tax_balance_dict.get(self.tax_line_id.name)
                if dest_tax and dest_tax.invoice_repartition_line_ids and self.account_id.code == dest_tax.invoice_repartition_line_ids.account_id.code:
                    self.name = f"{self.tax_line_id.name}"
                    self.tax_line_id = dest_tax


class account_chart_template(models.Model):
    """
        defaults for 4 digits in chart of accounts
     """
    _inherit = 'account.chart.template'

    
    def generate_fiscal_position(self, tax_template_ref, acc_template_ref, company):
        """ This method generate Fiscal Position, Fiscal Position Accounts and Fiscal Position Taxes from templates.

            :param chart_temp_id: Chart Template Id.
            :param taxes_ids: Taxes templates reference for generating account.fiscal.position.tax.
            :param acc_template_ref: Account templates reference for generating account.fiscal.position.account.
            :param company_id: company_id selected from wizard.multi.charts.accounts.
            :returns: True
        """
        #raise Warning('a ref %s' % tax_template_ref)
        
        res = super(account_chart_template, self).generate_fiscal_position(tax_template_ref, acc_template_ref, company)
        positions = self.env['account.fiscal.position.template'].search([('chart_template_id', '=', self.id)])
        for position in positions:
            template_xmlid = self.env['ir.model.data'].search(
                [('model', '=', position._name), ('res_id', '=', position.id)])
            new_xmlid = 'l10n_se.' + str(company.id) + '_' + template_xmlid.name
            new_fp = self.env.ref(new_xmlid)
            for balance in position.tax_balance_ids:
                self.create_record_with_xmlid(company, balance, 'account.fiscal.position.tax.balance', {
                    'tax_src_id': tax_template_ref[balance.tax_src_id.id],
                    'tax_dest_id': balance.tax_dest_id and tax_template_ref[balance.tax_dest_id.id] or False,
                    'position_id': new_fp.id
                })
            new_fp.auto_apply = position.auto_apply
            new_fp.vat_required = position.vat_required
            new_fp.country_id = position.country_id
            new_fp.country_group_id = position.country_group_id
        return res

