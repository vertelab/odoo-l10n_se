# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2013-2016 Vertel AB <http://vertel.se>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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

from odoo import api, models, fields, _
import re

import logging
_logger = logging.getLogger(__name__)


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    clearing_number = fields.Char(string='Clearing Number')

    def _compute_acc_type(self):
        for bank in self:
            if bank.acc_number and re.match('\d{3,4}-\d{4}', bank.acc_number):
                bank.acc_type = 'bankgiro'
            elif bank.acc_number and re.match('\d{5,7}-\d{1}', bank.acc_number):
                bank.acc_type = 'plusgiro'
            else:
                super(ResPartnerBank, bank)._compute_acc_type()
