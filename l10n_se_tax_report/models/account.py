# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2017 Vertel AB (<http://vertel.se>).
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

from odoo import api, fields, models, _
import logging
_logger = logging.getLogger(__name__)


# [0] när det är positiv/ja, [1] när det är negativ/nej
INK2S_MAPPING = {
    '4.1': ['7650', ''],
    '4.2': ['7750', ''],
    '4.3a': ['7651', ''],
    '4.3b': ['7652', ''],
    '4.3c': ['7653', ''],
    '4.6a': ['7654', ''],
    '4.6c': ['7655', ''],
    '4.7b': ['7656', ''],
    '4.7d': ['7657', ''],
    '4.7e': ['7658', ''],
    '4.8b': ['7659', ''],
    '4.8c': ['7660', ''],
    '4.10': ['7661', '7760'],
    '4.12': ['7662', ''],
    '4.13': ['7663', '7762'],
    '4.6e': ['7665', ''],
    '4.9': ['7666', '7765'],
    '4.6d': ['7667', ''],
    '4.6b': ['7668', ''],
    '4.15': ['7670', ''],
    '4.14b': ['7671', ''],
    '4.14c': ['7672', ''],
    '4.4a': ['7751', ''],
    '4.5a': ['7752', ''],
    '4.5b': ['7753', ''],
    '4.5c': ['7754', ''],
    '4.7a': ['7755', ''],
    '4.7c': ['7756', ''],
    '4.7f': ['7757', ''],
    '4.8a': ['7758', ''],
    '4.8d': ['7759', ''],
    '4.11': ['7761', ''],
    '4.14a': ['7763', ''],
    '4.4b': ['7764', ''],
    '4.16': ['7770', ''],
    '4.17': ['8020', ''],
    '4.18': ['8021', ''],
    '4.21': ['8022', ''],
    '4.19': ['8023', ''],
    '4.20': ['8026', ''],
    '4.22': ['8028', ''],
}


#~ https://www.skatteverket.se/foretagochorganisationer/arbetsgivare/lamnaarbetsgivardeklaration/hurlamnarjagarbetsgivardeklaration/saharfyllerduirutaforruta.4.3810a01c150939e893f18e43.html
class account_account(models.Model):
    _inherit = 'account.account'

class account_tax(models.Model):
    _inherit = 'account.tax'

    def get_taxlines(self, move_lines=None):
        move_lines = move_lines or self.env['account.move'].with_context(self._context)
        return move_lines.get_movelines().filtered(lambda r: r.tax_line_id in self)

    @api.model
    def get_taxtable(self):
        tax = {tax.code:line.balance for line in self.get_taxlines() for tax in line.mapped('tax_ids')}
        return tax



