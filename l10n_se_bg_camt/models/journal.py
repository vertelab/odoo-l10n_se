# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2004-2023 Vertel (<http://vertel.se>).
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

import logging

_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    is_bankgiro_journal = fields.Boolean(string="Is A Bankgiro Journal",help="This is used for the OCA Camt import function so that we can get the batch bankgiro sum to use to validate the bankgiro account.")
    
# ~ class AccountBankStatementImport(models.TransientModel):
    # ~ _inherit = "account.statement.import"

    # ~ def _parse_file(self, data_file):
        # ~ """Parse a CAMT053 XML file."""
        # ~ _logger.warning("_parse_file"*100)
        # ~ _logger.warning(f"{self._context=}")
        # ~ super(AccountBankStatementImport, self).with_context(is_bankgiro_journal=self.journal_id.is_bankgiro_journal)._parse_file(data_file)
