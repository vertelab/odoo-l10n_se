# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015-2016 Vertel (<http://www.vertel.se>).
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

from openerp import models, fields, api, _
from openerp.exceptions import Warning
from openerp import workflow
from lxml import etree

import logging
_logger = logging.getLogger(__name__)

class PaymentMode(models.Model):
    _inherit = 'payment.mode'

    is_seb_payment = fields.Boolean(string='SEB Payment', help="Will generate a payment file using pain.001.001.03 in the flavor that SEB wants.")

