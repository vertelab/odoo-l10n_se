# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2024 Vertel (<http://vertel.se>).
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
