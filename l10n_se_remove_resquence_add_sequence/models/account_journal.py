# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2004-2021 Vertel (<http://vertel.se>).
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
from dateutil.relativedelta import relativedelta
from odoo.modules.registry import Registry
from odoo.exceptions import except_orm, Warning, RedirectWarning
from odoo import models, fields, api, _
from odoo import tools

import logging
_logger = logging.getLogger(__name__)

class AccountJournal(models.Model):
    _inherit = 'account.journal'
    
    # ~ voucher_sequence = fields.Many2one(comodel_name='ir.sequence' , string='Voucher sequence', 
    # ~ help="This is the sequence used on the number field on a voucer, keep blank and the voucher number will be \"JOURNALNAME/YEAR/MONTH/NUMBER\"")
    
    secure_sequence_id = fields.Many2one('ir.sequence',
    help='Sequence to use to ensure the securisation of data',
    check_company=True,
    readonly=False, copy=False)

# ~ class AccountMove(models.Model):
    # ~ _inherit = 'account.move'
    
    # ~ @api.depends('journal_id', 'date')
    # ~ def _get_last_sequence(self):
        # ~ if !journal_id.voucher_sequence:
            # ~ return super(AccountMove,self)._get_last_sequence()

